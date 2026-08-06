from __future__ import annotations

from typing import Any

from .models import SourceChunk

_SYSTEM_PROMPT = """You are a meticulous legal research assistant. Answer questions strictly from the context sources provided below.

Rules:
1. Ground every factual statement in the numbered context sources.
2. Cite sources inline with square-bracket markers, e.g. [1], [2], [1,3]. Put the marker immediately after the claim it supports.
3. If the context does not contain the information needed to answer, say so explicitly and do not guess.
4. When referring to a statute, regulation, or judgment, name the section, article, or paragraph and cite the source that supports it.
5. Never invent citations, case names, statutes, or facts. Never repeat a claim you cannot trace to a source.
6. Flag ambiguity or conflicting sources rather than papering over them.
7. Be concise, precise, and neutral. Use plain legal language. Answer in the same language as the question.
8. Do not provide legal advice; present research findings grounded in the provided sources."""

_STRUCTURED_OUTPUT_RULE = (
    "Output a single JSON object only. Do not include any text outside the JSON object."
)

_JSON_SYSTEM_PROMPT = _SYSTEM_PROMPT + "\n\n" + _STRUCTURED_OUTPUT_RULE

_QUERY_TEMPLATE = """Answer the question using ONLY the numbered context sources below.

### CONTEXT

{context}

### CONVERSATION

{conversation}

### QUESTION

{question}

Give a grounded answer with inline [n] citations. If the sources do not contain enough information, state that the answer cannot be grounded in the provided sources."""

_EMPTY_CONVERSATION = "(no prior conversation)"

_VERIFIER_SYSTEM_PROMPT = """You are a strict legal fact-checker. Given a context and an answer, decide for every claim in the answer whether it is supported by the context. Do not rely on outside knowledge.

Output a single JSON object with this exact shape:
{
  "unsupported_claims": ["<claim text>", ...],
  "supported_claims": ["<claim text>", ...]
}

List each claim as a short verbatim quote from the answer. If every claim is supported, return an empty unsupported_claims array."""

_VERIFIER_TEMPLATE = """### CONTEXT

{context}

### ANSWER TO CHECK

{answer}

### QUESTION

{question}

Output the JSON verdict only."""


def _conversation_block(messages: list[dict[str, str]] | None) -> str:
    if not messages:
        return _EMPTY_CONVERSATION
    lines = []
    for message in messages:
        role = "User" if message.get("role") == "user" else "Assistant"
        lines.append(f"{role}: {message.get('content', '')}")
    return "\n".join(lines)


class PromptBuilder:
    def __init__(
        self,
        json_instruction: bool = True,
        include_grounding: bool = True,
    ) -> None:
        self._json_instruction = json_instruction
        self._include_grounding = include_grounding

    def build_system(self, json_mode: bool = False) -> str:
        if json_mode and self._json_instruction:
            return _JSON_SYSTEM_PROMPT
        return _SYSTEM_PROMPT

    def build_context(self, chunks: list[SourceChunk]) -> str:
        blocks: list[str] = []
        for chunk in chunks:
            header = chunk.doc_title or chunk.source_file or f"Source {chunk.index}"
            parts = [header]
            if chunk.section_number or chunk.section:
                section = " ".join(
                    part for part in (chunk.section_number, chunk.section) if part
                )
                parts.append(f"Section: {section}")
            if chunk.page is not None:
                parts.append(f"Page: {chunk.page}")
            blocks.append(f"[{chunk.index}] ({'; '.join(parts[1:]) or header})\n{chunk.text}")
        return "### CONTEXT\n\n" + "\n\n".join(blocks)

    def build_query(
        self,
        query: str,
        chunks: list[SourceChunk],
        history: list[dict[str, str]] | None = None,
    ) -> str:
        return _QUERY_TEMPLATE.format(
            context=self.build_context(chunks),
            conversation=_conversation_block(history),
            question=query,
        )

    def build_messages(
        self,
        query: str,
        chunks: list[SourceChunk],
        history: list[dict[str, str]] | None = None,
        json_mode: bool = False,
    ) -> tuple[str, str]:
        system = self.build_system(json_mode=json_mode)
        prompt = self.build_query(query, chunks, history)
        return system, prompt

    def build_claim_verification_prompt(
        self,
        query: str,
        answer: str,
        chunks: list[SourceChunk],
    ) -> str:
        return _VERIFIER_TEMPLATE.format(
            context=self.build_context(chunks),
            answer=answer,
            question=query,
        )

    def build_claim_verifier_system(self) -> str:
        return _VERIFIER_SYSTEM_PROMPT
