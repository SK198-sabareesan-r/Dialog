"""
Chat Session Service — PostgreSQL-backed conversation history.

Tables:
  chat_sessions: id, user_id, title, created_at, updated_at
  chat_messages: id, session_id, role, content, citations, language, duration_ms, created_at
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from .models import ChatSession, ChatMessage
from .database import engine, Base
from utils.logger import get_logger

logger = get_logger(__name__)


class ChatSessionService:
    """CRUD operations for chat sessions."""

    def init_db(self):
        """Create tables if they don't exist."""
        Base.metadata.create_all(bind=engine)
        logger.info("Chat session tables initialized")

    def create_session(self, db: Session, user_id: str, first_message: str = "") -> Dict[str, Any]:
        """Create a new chat session."""
        title = self._generate_title(first_message)
        session = ChatSession(user_id=user_id, title=title)
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"Created session {session.id} for user {user_id}")
        return self._session_to_dict(session)

    def list_sessions(self, db: Session, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """List all sessions for a user, most recent first."""
        sessions = (
            db.query(ChatSession)
            .filter(ChatSession.user_id == user_id)
            .order_by(ChatSession.updated_at.desc())
            .limit(limit)
            .all()
        )
        return [self._session_to_dict(s, include_messages=False) for s in sessions]

    def get_session(self, db: Session, user_id: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Get a session with all messages."""
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            return None
        return self._session_to_dict(session, include_messages=True)

    def add_message(
        self,
        db: Session,
        user_id: str,
        session_id: str,
        user_text: str,
        assistant_answer: str,
        citations: Optional[List[Dict]] = None,
        language: Optional[Dict] = None,
        duration_ms: float = 0,
    ) -> Optional[Dict[str, Any]]:
        """Append a user+assistant message pair to a session."""
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            return None

        user_msg = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_text,
        )
        assistant_msg = ChatMessage(
            session_id=session_id,
            role="assistant",
            content=assistant_answer,
            citations=self._clean_citations(citations) if citations else None,
            language=language,
            duration_ms=duration_ms,
        )

        db.add(user_msg)
        db.add(assistant_msg)

        session.updated_at = datetime.utcnow()
        if session.title == "New conversation":
            session.title = self._generate_title(user_text)

        db.commit()

        return {
            "user": self._message_to_dict(user_msg),
            "assistant": self._message_to_dict(assistant_msg),
        }

    def delete_session(self, db: Session, user_id: str, session_id: str) -> bool:
        """Delete a session and all its messages."""
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            return False
        db.delete(session)
        db.commit()
        logger.info(f"Deleted session {session_id}")
        return True

    def update_title(self, db: Session, user_id: str, session_id: str, title: str) -> bool:
        """Rename a session."""
        session = (
            db.query(ChatSession)
            .filter(ChatSession.id == session_id, ChatSession.user_id == user_id)
            .first()
        )
        if not session:
            return False
        session.title = title
        session.updated_at = datetime.utcnow()
        db.commit()
        return True

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _generate_title(self, text: str) -> str:
        if not text or not text.strip():
            return "New conversation"
        clean = text.strip().replace("\n", " ")
        return clean[:57] + "..." if len(clean) > 60 else clean

    def _clean_citations(self, citations: List[Dict]) -> List[Dict]:
        clean = []
        for c in citations:
            clean.append({
                "source_file": c.get("source_file", ""),
                "s3_uri": c.get("s3_uri", ""),
                "score": c.get("score", 0),
            })
        return clean

    def _session_to_dict(self, session: ChatSession, include_messages: bool = True) -> Dict[str, Any]:
        result = {
            "id": session.id,
            "user_id": session.user_id,
            "title": session.title,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        }
        if include_messages:
            result["messages"] = [self._message_to_dict(m) for m in session.messages]
        return result

    def _message_to_dict(self, msg: ChatMessage) -> Dict[str, Any]:
        return {
            "id": msg.id,
            "role": msg.role,
            "content": msg.content,
            "citations": msg.citations,
            "language": msg.language,
            "duration_ms": msg.duration_ms,
            "created_at": msg.created_at.isoformat() if msg.created_at else None,
        }


chat_session_service = ChatSessionService()
