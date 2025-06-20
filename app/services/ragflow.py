import logging
import re
import pandas as pd
from io import BytesIO
from typing import List
from ragflow_sdk.modules.session import Message
from ragflow_sdk import RAGFlow, Session, Chat
from app.config.setting import settings

logger = logging.getLogger("celery")

RAGFLOW_API_KEY = settings.RAGFLOW_API_KEY
RAGFLOW_BASE_URL = settings.RAGFLOW_BASE_URL
TENDER_KNOWLEDGE_BASE = settings.TENDER_KNOWLEDGE_BASE
TENDER_QUESTION_HEADER = settings.TENDER_QUESTION_HEADER


# parse input file bytes using Pandas DataFrame for column "Requirement" and output list of srings
def parse_input_file(input_file: bytes) -> tuple[list[str], pd.DataFrame]:
    # Read the Excel file into a DataFrame
    df = pd.read_excel(BytesIO(input_file))

    # Check if the "Requirement" column exists
    if "Requirement" not in df.columns:
        raise ValueError("The input file must contain a 'Requirement' column.")

    # Extract the "Requirement" column and convert it to a list of strings
    requirements = df["Requirement"].dropna().astype(str).tolist()
    if not requirements:
        raise ValueError("The 'Requirement' column is empty or contains no valid data.")
    return (requirements, df)


# obtain the chat assistant object
def get_chat_assistant(
    api_key=RAGFLOW_API_KEY,
    base_url=RAGFLOW_BASE_URL,
    assistant_name=TENDER_KNOWLEDGE_BASE,
) -> list[Chat]:
    rag_object = RAGFlow(api_key=api_key, base_url=base_url)
    logger.info("RAGFlow object created")
    assistant_list = rag_object.list_chats(name=assistant_name)
    if assistant_list:
        return assistant_list[0]
    else:
        raise ValueError("Assistant not found")


# create an new instance of RAGFlow session with the API key, base URL and the assistant name
def get_chat_assistant_session(
    api_key=RAGFLOW_API_KEY,
    base_url=RAGFLOW_BASE_URL,
    assistant_name=TENDER_KNOWLEDGE_BASE,
    session_name="SeismaTenderSession",
) -> Session:
    assistant = get_chat_assistant(api_key, base_url, assistant_name)
    logger.info(f"assistant fetched with name = {assistant.name}")

    new_session = assistant.create_session(name=session_name)
    logger.info(
        f"Created new session.id: {new_session.id}, "
        f"session.name: {new_session.name}, "
        f"session.messages: {new_session.messages}, "
        f"session.chat_id: {new_session.chat_id}"
    )
    return new_session


# ask a question to the chat assistant session
def ask_question_to_chat_assistant(
    session: Session, question: str, stream: bool = False
) -> dict:
    """
    Ask a question to the chat assistant session.

    Args:
        session (Session): The chat assistant session object.
        question (str): The question to ask.
        stream (bool, optional): Whether to stream the response. Defaults to False.

    Returns:
        dict: The response from the chat assistant.
    """
    """
    Sends a question to the chat assistant session and retrieves the response.

    Args:
        session (Session): The RAGFlow session object to interact with.
        question (str): The question to be asked.
        stream (bool, optional): Whether to stream the response. Defaults to False.

    Returns:
        dict: The response from the chat assistant in JSON format.

    Raises:
        ValueError: If the response status is not 200 or if the API call fails.
    """
    logger.info(f"Asked raw question: {question}")
    if TENDER_QUESTION_HEADER not in question:
        question = TENDER_QUESTION_HEADER + question
        logger.info(f"Amended question: {question}")
    # message = session.ask(question=question, stream=stream)
    json_data = {"question": question, "stream": stream, "session_id": session.id}
    res = session.post(
        f"/chats/{session.chat_id}/completions", json_data, stream=stream
    )
    logger.info(f"Response status: {res.status_code}")
    if res.status_code == 200:
        return res.json()
    else:
        raise ValueError("Failed to get response from RAG Flow API")


def ask_questions_to_chat_assistant(
    session: Session, questions: list[str], stream: bool = False
):  # -> Union[Message, Iterator[Message]]:
    output = []
    logger.info(f"stream={stream}")
    for question_raw in questions:
        single_answer = ask_question_to_chat_assistant(
            session=session, question=question_raw, stream=stream
        )
        if single_answer:
            output.append([question_raw, single_answer])

    return output


def parse_single_answer(response: List) -> dict:
    """
    Parse a single response from the chat assistant response.

    Args:
        response (List): The response list from the chat assistant.

    Returns:
        dict: Parsed answer containing answer text, and reference.
    """
    logger.info(f"RAG query response: {response}")
    try:
        response_text = response["data"]["answer"]
        # remove substring such as ##d$$ from the response, where d is a digit or digits
        if response_text:
            response_text = re.sub(r"##\d+\$\$", "", response_text)
        reference = response["data"].get("reference", {}).get("doc_aggs", "")
        if reference:
            ref_list = [ref["doc_name"] for ref in reference]
            # concate strings in ref_list with '\n'
            reference = "\n".join(ref_list)
    except (IndexError, KeyError, TypeError) as e:
        logger.error(f"Error parsing single answer: {response} due to: {e}")
        response_text = ""
        reference = ""
    return {
        "Supplier explanation / comments": response_text,
        "Reference": reference,
    }
