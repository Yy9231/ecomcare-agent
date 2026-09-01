import asyncio
import json
from pathlib import Path

from app.database import SessionLocal
from app.services.knowledge import search_knowledge
from app.services.router import deterministic_route


async def evaluate() -> dict:
    case_path = Path(__file__).parents[2] / "evaluation" / "cases.jsonl"
    cases = [json.loads(line) for line in case_path.read_text().splitlines() if line.strip()]
    routing_cases = [case for case in cases if case["kind"] == "routing"]
    safety_cases = [case for case in cases if case["kind"] == "safety"]
    retrieval_cases = [case for case in cases if case["kind"] == "retrieval"]
    routing_hits = 0
    task_hits = 0
    for case in routing_cases:
        decision = deterministic_route(case["query"])
        routing_hits += decision.intent == case["expected_intent"]
        order_ok = not case.get("expected_order") or decision.order_no == case["expected_order"]
        task_hits += decision.intent == case["expected_intent"] and order_ok
    safety_hits = sum(
        deterministic_route(case["query"]).intent == case["expected_intent"]
        for case in safety_cases
    )
    retrieval_hits = 0
    async with SessionLocal() as session:
        for case in retrieval_cases:
            results = await search_knowledge(session, case["query"])
            retrieval_hits += any(case["expected_source"] in item["source"] for item in results)
    total_tasks = len(routing_cases) + len(safety_cases)
    return {
        "case_count": len(cases),
        "tool_selection_accuracy": round(routing_hits / len(routing_cases), 4),
        "task_completion_rate": round((task_hits + safety_hits) / total_tasks, 4),
        "rag_recall_at_3": round(retrieval_hits / len(retrieval_cases), 4),
        "unsafe_action_block_rate": round(safety_hits / len(safety_cases), 4),
        "notes": "Offline deterministic router and seeded pgvector corpus; no LLM cost incurred.",
    }


def main() -> None:
    print(json.dumps(asyncio.run(evaluate()), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
