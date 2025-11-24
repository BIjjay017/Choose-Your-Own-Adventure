from uuid import uuid4
from dotenv import load_dotenv
from pydantic import ValidationError
from sqlalchemy.orm import Session
from datetime import datetime

from groq import Groq
from langchain_core.output_parsers import PydanticOutputParser

from core.prompt import STORY_PROMPT
from models.story import Story, StoryNode
from core.models import StoryLLMResponse, StoryNodeLLM
from models.job import StoryJob
from core.config import settings

import re

load_dotenv()

class StoryGenerator:

    @staticmethod
    def _extract_json_from_code_block(text: str) -> str:
        """Remove any ```json or ``` code block markers from LLM output."""
        return re.sub(r"^```(?:json)?\n|```$", "", text.strip(), flags=re.MULTILINE)

    @classmethod
    def generate_story(cls, db: Session, session_id: str, theme: str = "fantasy") -> Story:
        """
        Generate a story using Groq LLM, parse it, save it to the database, and track job status.
        """
        job_id = str(uuid4())
        job = StoryJob(
            job_id=job_id,
            session_id=session_id,
            theme=theme,
            status="pending",
            created_at=datetime.utcnow()
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        try:
            client = Groq(api_key=settings.GROQ_API_KEY)
            story_parser = PydanticOutputParser(pydantic_object=StoryLLMResponse)

            # Prepare prompts
            system_msg = {"role": "system", "content": STORY_PROMPT}
            user_msg = {
                "role": "user",
                "content": f"Create the story with this theme: {theme}\n\n"
                           f"Follow these instructions:\n{story_parser.get_format_instructions()}"
            }

            # Call Groq
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[system_msg, user_msg]
            )

            # Extract raw text safely
            raw_text = response.choices[0].message.content

            # Strip triple backticks (common in LLM responses)
            if raw_text.startswith("```") and raw_text.endswith("```"):
                lines = raw_text.splitlines()
                # Remove first line (```json or ```) and last line (```)
                raw_text = "\n".join(lines[1:-1])

            # Remove leading/trailing whitespace
            raw_text = raw_text.strip()

            if not raw_text:
                raise ValueError("LLM returned empty response")

            # Parse into Pydantic structure
            story_structure = story_parser.parse(raw_text)

            # Save main story row
            story_db = Story(title=story_structure.title, session_id=session_id)
            db.add(story_db)
            db.flush()
            db.refresh(story_db)

            if not story_db.id:
                raise ValueError(f"Failed to save story to DB: {story_db}")

            # Process root node
            root_node_data = story_structure.rootNode
            if isinstance(root_node_data, dict):
                root_node_data = StoryNodeLLM.model_validate(root_node_data)

            cls._process_story_node(db, story_db.id, root_node_data, is_root=True)

            # Update job on success
            job.status = "completed"
            job.story_id = story_db.id
            job.completed_at = datetime.utcnow()
            db.commit()

            return story_db

        except Exception as e:
            db.rollback()
            # Update job on failure
            job.status = "failed"
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            db.add(job)
            db.commit()
            print(f"[StoryGenerator] Failed to generate story: {e}")
            raise

    @classmethod
    def _process_story_node(cls, db: Session, story_id: int, node_data: StoryNodeLLM,
                            is_root: bool = False) -> StoryNode:

        # Create the StoryNode database object
        node = StoryNode(
            story_id=story_id,
            content=node_data.content,
            is_root=is_root,
            is_ending=node_data.isEnding,
            is_winning_ending=node_data.isWinningEnding,
            options=[]
        )

        db.add(node)
        db.flush()
        db.refresh(node)

        # Process child options only if available
        if not node.is_ending and node_data.options:

            options_list = []

            for option in node_data.options:

                next_node_data = option.nextNode  # Always exists in your schema

                # Convert dict → Pydantic object if needed
                if isinstance(next_node_data, dict):
                    next_node_obj = StoryNodeLLM.model_validate(next_node_data)
                else:
                    next_node_obj = next_node_data

                # Recursive: create child node in DB
                child_node = cls._process_story_node(
                    db,
                    story_id,
                    next_node_obj,
                    is_root=False
                )

                # Add option with text + reference to child DB node
                options_list.append({
                    "text": option.text,
                    "node_id": child_node.id
                })

            # Save options JSON array in DB
            node.options = options_list
            db.flush()

        return node


