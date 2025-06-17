import os
import pandas as pd
from datetime import datetime
from app.tasks.celery_worker import celery_app  # Import the Celery app
from celery.utils.log import get_task_logger
from app.config.setting import settings
from app.models.task_schemas import TaskStatus, TaskResult
from app.utils.file_client import get_processed_file_directory
from app.services.ragflow import (
    parse_input_file,
    get_chat_assistant_session,
    ask_question_to_chat_assistant,
    parse_single_answer,
)
from app.services.gemini import query_google_gemini


logger = get_task_logger(__name__)
# Temporary storage (replace with Redis/DB in production)
tasks = {}
stream = settings.RAGFLOW_STREAM.lower() == "true"  # Convert to boolean


@celery_app.task(bind=True)
def process_excel(self, filename: str, contents: bytes):
    task_id = self.request.id
    logger.info(
        f"For RagFlow AI, Celery worker: {task_id} statrt processing file: {filename}"
    )

    # Initialize TaskResult
    task_result = TaskResult(
        task_id=task_id,
        status=TaskStatus.STARTED,
        filename=filename,
        progress=0.0,
        processed_at=None,
        download_path=None,
        error=None,
    )
    try:
        # obtain the current directory of the project
        output_dir = get_processed_file_directory(settings.PROCESSED_FILE_DIR)
        # update celery task state
        self.update_state(state=TaskStatus.STARTED, meta=task_result.model_dump())
        logger.info(f"Before processing excel file, Task result: {task_result}")

        # Step 1: extract requirements from the input file
        (requirements, _) = parse_input_file(contents)

        # Step 2: Create a new session with the chat assistant
        session = get_chat_assistant_session()

        # Update progress to 1% to indicate that the task has started.
        task_result.progress = 1.0
        task_result.status = TaskStatus.PROCESSING
        self.update_state(state=TaskStatus.PROCESSING, meta=task_result.model_dump())
        logger.info(f"After set chat session, Task result: {task_result}")

        # Step 3: Ask the question to the chat assistant
        parsed_responses = {
            "Requirement": [],
            "Supplier explanation / comments": [],
            "Reference": [],
        }
        total_questions = len(requirements)
        for i in range(total_questions):
            question_raw = requirements[i]
            logger.info(
                f"Processing question {i + 1}/{total_questions}: {question_raw}"
            )

            single_answer = ask_question_to_chat_assistant(
                session=session, question=question_raw, stream=stream
            )
            need_public_llm = True
            if single_answer:
                # Step 4a: Extract the answers and references from the responses from RAGFlow
                parsed_single_answer = parse_single_answer(single_answer)
                ragflow_anwer = parsed_single_answer["Supplier explanation / comments"]
                if (
                    ragflow_anwer
                    and settings.NULL_RAGFLOW_ANSWER
                    not in ragflow_anwer.strip().lower()
                ):
                    # Append the parsed answers to the parsed_responses dictionaryragflow_anwer
                    parsed_responses["Requirement"].append(question_raw)
                    parsed_responses["Supplier explanation / comments"].append(
                        parsed_single_answer["Supplier explanation / comments"]
                    )
                    parsed_responses["Reference"].append(
                        parsed_single_answer["Reference"]
                    )
                    # Found in RAGFlow, no need to query public LLM
                    need_public_llm = False
            if need_public_llm:
                # Step 4b: If no answer found in RAGFlow, query public LLM (default Google Gemini)
                question = question_raw
                if settings.VENDOR_QUESTION_HEADER not in question:
                    question = settings.VENDOR_QUESTION_HEADER + question
                    logger.info(f"Amended question for public LLM: {question}")
                try:
                    # Query public LLM (Google Gemini)
                    single_answer = query_google_gemini(
                        query=question, model=settings.PUBLIC_LLM_MODEL
                    )
                    if single_answer:
                        # Append the public LLM answer to the parsed_responses dictionary
                        parsed_responses["Requirement"].append(question_raw)
                        parsed_responses["Supplier explanation / comments"].append(
                            single_answer
                        )
                        parsed_responses["Reference"].append(settings.PUBLIC_LLM_MODEL)
                    else:
                        raise ValueError("No answer returned from public LLM.")
                except Exception as e:
                    logger.error(
                        (
                            f"Error querying public LLM {settings.PUBLIC_LLM_MODEL} "
                            f"for question {question_raw}: {str(e)}"
                        )
                    )
                    parsed_responses["Requirement"].append(question_raw)
                    parsed_responses["Supplier explanation / comments"].append(
                        "Error: Unable to get answer from RAG and public LLM."
                    )
                    parsed_responses["Reference"].append("Error")

            # Update progress
            task_result.progress = round((i + 1) / total_questions * 100, 1)
            task_result.status = TaskStatus.PROCESSING

            # Update Celery task state
            self.update_state(
                state=TaskStatus.PROCESSING, meta=task_result.model_dump()
            )

        # Step 5: Add the extracted information to the dataframe
        # initialize a new empty dataframe without using the original one
        df = pd.DataFrame()
        df["Requirement"] = parsed_responses["Requirement"]
        df["Supplier explanation / comments"] = parsed_responses[
            "Supplier explanation / comments"
        ]
        df["Reference"] = parsed_responses["Reference"]
        # logger.info(f"Final response>:\n {df}")

        # Step 6: Save the dataframe to an Excel file
        # convert current time to string in format of HHMMSS
        current_time = datetime.now().strftime("%H%M%S")
        # get file name without extension
        filename_without_extension = os.path.splitext(filename)[0]
        output_filename = (
            f"processed_{filename_without_extension}_{task_id}_{current_time}.xlsx"
        )
        output_path = os.path.join(output_dir, output_filename)
        # Save the dataframe to an Excel file
        with pd.ExcelWriter(output_path, engine="xlsxwriter") as writer:
            df.to_excel(writer, index=False, sheet_name="SeismaTender")
            workbook = writer.book
            worksheet = writer.sheets["SeismaTender"]
            # Define format for wrapped text
            wrap_format = workbook.add_format({"text_wrap": True, "valign": "top"})

            # Set column widths and apply text wrap
            worksheet.set_column(
                "A:A", settings.Q_COLUMN_WIDTH, wrap_format
            )  # Column 'Requirement'
            worksheet.set_column(
                "B:B", settings.A_COLUMN_WIDTH, wrap_format
            )  # Column 'Answer'
            worksheet.set_column(
                "C:C", settings.REF_COLUMN_WIDTH, wrap_format
            )  # Column 'Reference'

        # Update final result
        task_result.status = TaskStatus.SUCCESS
        task_result.progress = 100.0
        task_result.download_path = output_path
        task_result.processed_at = datetime.now()
        # Update Celery task state to SUCCESS
        self.update_state(state=TaskStatus.SUCCESS, meta=task_result.model_dump())

        # Store in temporary storage
        tasks[task_id] = task_result

        return task_result.model_dump()

    except Exception as e:
        # using existing task_result to update the task status

        logger.error(f"An error occurred during task: {task_id} processing: {str(e)}")
        task_result.status = TaskStatus.FAILURE
        task_result.progress = 0.0  # Set progress to 0 on failure
        task_result.error = str(e)
        task_result.processed_at = datetime.now()
        tasks[task_id] = task_result
        # no need to update FAILURE state as celery will do it automatically. just raise
        raise
