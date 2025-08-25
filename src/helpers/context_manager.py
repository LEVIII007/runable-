import json
import hashlib
import os
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict
from src.config.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ContextChunk:
    """A chunk of context information"""
    id: str
    content: str
    type: str  # "code", "execution_result", "file", "conversation"
    language: Optional[str] = None
    file_path: Optional[str] = None
    timestamp: float = 0.0
    importance_score: float = 0.0
    token_count: int = 0
    
    def __post_init__(self):
        if self.timestamp == 0.0:
            self.timestamp = time.time()
        if self.token_count == 0:
            # Rough token estimation (4 chars per token)
            self.token_count = len(self.content) // 4


@dataclass
class ContextSession:
    """Context session containing multiple chunks"""
    session_id: str
    chunks: List[ContextChunk]
    total_tokens: int = 0
    created_at: float = 0.0
    last_accessed: float = 0.0
    
    def __post_init__(self):
        if self.created_at == 0.0:
            self.created_at = time.time()
        self.last_accessed = time.time()
        self._update_total_tokens()
    
    def _update_total_tokens(self):
        self.total_tokens = sum(chunk.token_count for chunk in self.chunks)


class ContextManager:
    """Manages context for coding sessions with intelligent pruning and persistence"""
    
    def __init__(self, 
                 storage_path: str = "./context_storage",
                 max_tokens_per_session: int = 50000,  # Conservative limit for context
                 max_chunks_per_session: int = 100):
        
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.max_tokens_per_session = max_tokens_per_session
        self.max_chunks_per_session = max_chunks_per_session
        self.sessions: Dict[str, ContextSession] = {}
        
        # Load existing sessions
        self._load_sessions()
    
    def _generate_chunk_id(self, content: str, chunk_type: str) -> str:
        """Generate unique ID for content chunk"""
        content_hash = hashlib.md5(f"{content}{chunk_type}{time.time()}".encode()).hexdigest()
        return f"{chunk_type}_{content_hash[:12]}"
    
    def _calculate_importance_score(self, chunk: ContextChunk, session: ContextSession) -> float:
        """Calculate importance score for a chunk"""
        score = 0.0
        
        # Recency score (newer is more important)
        current_time = time.time()
        recency_weight = 1.0 - min((current_time - chunk.timestamp) / 3600, 0.8)  # Max 1 hour decay
        score += recency_weight * 0.3
        
        # Type importance
        type_weights = {
            "execution_result": 0.4,
            "code": 0.3,
            "file": 0.2,
            "conversation": 0.1
        }
        score += type_weights.get(chunk.type, 0.1) * 0.3
        
        # Length importance (moderate length is often most important)
        length_score = min(chunk.token_count / 1000, 1.0)  # Normalized to 1000 tokens
        if length_score > 0.1:  # Avoid too short chunks
            score += length_score * 0.2
        
        # Error/success importance
        if chunk.type == "execution_result":
            if "error" in chunk.content.lower() or "failed" in chunk.content.lower():
                score += 0.2  # Errors are important for debugging
            elif "success" in chunk.content.lower() or "✅" in chunk.content:
                score += 0.1
        
        return min(score, 1.0)
    
    def _prune_session(self, session: ContextSession) -> ContextSession:
        """Prune session to stay within limits using intelligent selection"""
        
        if (session.total_tokens <= self.max_tokens_per_session and 
            len(session.chunks) <= self.max_chunks_per_session):
            return session
        
        # Calculate importance scores
        for chunk in session.chunks:
            chunk.importance_score = self._calculate_importance_score(chunk, session)
        
        # Sort by importance (descending)
        sorted_chunks = sorted(session.chunks, key=lambda x: x.importance_score, reverse=True)
        
        # Keep most important chunks within limits
        pruned_chunks = []
        total_tokens = 0
        
        for chunk in sorted_chunks:
            if (len(pruned_chunks) < self.max_chunks_per_session and 
                total_tokens + chunk.token_count <= self.max_tokens_per_session):
                pruned_chunks.append(chunk)
                total_tokens += chunk.token_count
            else:
                break
        
        # Ensure we keep at least the most recent chunks if importance pruning is too aggressive
        if len(pruned_chunks) < max(5, len(session.chunks) // 4):
            recent_chunks = sorted(session.chunks, key=lambda x: x.timestamp, reverse=True)
            for chunk in recent_chunks[:max(5, len(session.chunks) // 4)]:
                if chunk not in pruned_chunks:
                    if total_tokens + chunk.token_count <= self.max_tokens_per_session:
                        pruned_chunks.append(chunk)
                        total_tokens += chunk.token_count
        
        logger.info(f"Pruned session {session.session_id}: {len(session.chunks)} -> {len(pruned_chunks)} chunks")
        
        session.chunks = pruned_chunks
        session._update_total_tokens()
        return session
    
    def _save_session(self, session: ContextSession):
        """Save session to persistent storage"""
        try:
            session_file = self.storage_path / f"{session.session_id}.json"
            session_data = asdict(session)
            
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to save session {session.session_id}: {str(e)}")
    
    def _load_sessions(self):
        """Load sessions from persistent storage"""
        try:
            for session_file in self.storage_path.glob("*.json"):
                try:
                    with open(session_file, 'r') as f:
                        session_data = json.load(f)
                    
                    # Reconstruct ContextChunk objects
                    chunks = [ContextChunk(**chunk_data) for chunk_data in session_data["chunks"]]
                    
                    session = ContextSession(
                        session_id=session_data["session_id"],
                        chunks=chunks,
                        created_at=session_data.get("created_at", time.time()),
                        last_accessed=session_data.get("last_accessed", time.time())
                    )
                    
                    self.sessions[session.session_id] = session
                    
                except Exception as e:
                    logger.error(f"Failed to load session from {session_file}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Failed to load sessions: {str(e)}")
    
    def add_code_context(self, session_id: str, code: str, language: str = "python", file_path: Optional[str] = None) -> str:
        """Add code context to session"""
        
        chunk_id = self._generate_chunk_id(code, "code")
        chunk = ContextChunk(
            id=chunk_id,
            content=code,
            type="code",
            language=language,
            file_path=file_path
        )
        
        return self._add_chunk(session_id, chunk)
    
    def add_execution_result(self, session_id: str, result: str, success: bool = True) -> str:
        """Add execution result to session"""
        
        chunk_id = self._generate_chunk_id(result, "execution_result")
        chunk = ContextChunk(
            id=chunk_id,
            content=f"{'✅' if success else '❌'} {result}",
            type="execution_result"
        )
        
        return self._add_chunk(session_id, chunk)
    
    def add_conversation_context(self, session_id: str, message: str) -> str:
        """Add conversation message to session"""
        
        chunk_id = self._generate_chunk_id(message, "conversation")
        chunk = ContextChunk(
            id=chunk_id,
            content=message,
            type="conversation"
        )
        
        return self._add_chunk(session_id, chunk)
    
    def _add_chunk(self, session_id: str, chunk: ContextChunk) -> str:
        """Add chunk to session with automatic pruning"""
        
        if session_id not in self.sessions:
            self.sessions[session_id] = ContextSession(
                session_id=session_id,
                chunks=[]
            )
        
        session = self.sessions[session_id]
        session.chunks.append(chunk)
        session.last_accessed = time.time()
        session._update_total_tokens()
        
        # Prune if necessary
        session = self._prune_session(session)
        self.sessions[session_id] = session
        
        # Save to storage
        self._save_session(session)
        
        logger.debug(f"Added chunk {chunk.id} to session {session_id}")
        return chunk.id
    
    def get_session_context(self, session_id: str, max_tokens: Optional[int] = None) -> List[ContextChunk]:
        """Get context for a session, optionally limited by tokens"""
        
        if session_id not in self.sessions:
            return []
        
        session = self.sessions[session_id]
        session.last_accessed = time.time()
        
        if max_tokens is None:
            return session.chunks
        
        # Return chunks within token limit, prioritizing by importance
        sorted_chunks = sorted(session.chunks, key=lambda x: x.importance_score, reverse=True)
        
        selected_chunks = []
        total_tokens = 0
        
        for chunk in sorted_chunks:
            if total_tokens + chunk.token_count <= max_tokens:
                selected_chunks.append(chunk)
                total_tokens += chunk.token_count
            else:
                break
        
        # Sort selected chunks by timestamp for coherent context
        selected_chunks.sort(key=lambda x: x.timestamp)
        
        return selected_chunks
    
    def build_context_prompt(self, session_id: str, max_tokens: int = 8000) -> str:
        """Build a context prompt for the LLM from session history"""
        
        chunks = self.get_session_context(session_id, max_tokens)
        
        if not chunks:
            return "No previous context available."
        
        context_parts = []
        context_parts.append("=== Previous Context ===\n")
        
        for chunk in chunks:
            header = f"[{chunk.type.upper()}]"
            if chunk.file_path:
                header += f" {chunk.file_path}"
            if chunk.language:
                header += f" ({chunk.language})"
            
            context_parts.append(f"{header}:")
            context_parts.append(chunk.content)
            context_parts.append("")  # Empty line separator
        
        context_parts.append("=== End Context ===\n")
        
        return "\n".join(context_parts)


# Global context manager instance
_context_manager: Optional[ContextManager] = None

def get_context_manager() -> ContextManager:
    """Get or create the global context manager instance"""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextManager()
    return _context_manager 