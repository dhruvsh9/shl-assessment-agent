# Approach

## Design

I implemented a FastAPI service with two endpoints: `GET /health` and `POST /chat`. The API is stateless: every `/chat` call receives the full conversation history, and the agent reconstructs the current intent from those messages. The response is always produced through Pydantic models matching the required schema, so clarification, refusal, comparison, and recommendation replies all remain schema compliant.

I chose a free deterministic stack instead of a required LLM API. This avoids paid dependencies, reduces latency, and prevents hallucinated recommendations. An LLM can be added later for wording or intent extraction, but it is not needed for the evaluator-critical path.

## Catalog and Retrieval

The app loads `app/data/shl_catalog.json`, where each assessment has `name`, `url`, `test_type`, `description`, and keywords. Recommendations are generated only from this file. The checked-in catalog is an offline Individual Test Solutions snapshot so production behavior is deterministic and does not depend on live scraping. A scraper is included in `scripts/scrape_catalog.py` to refresh the JSON if SHL exposes the legacy product-catalog table; pre-packaged job solutions should be excluded during catalog preparation.

Retrieval uses lightweight hybrid scoring: exact token matches, assessment-name boosts, role synonym expansion, and test-type boosts. For example, Java developer queries boost Java and programming tests; stakeholder or communication requirements boost behavioral/personality assessments; personality refinements boost OPQ/MQ-style assessments. Results are capped to 10 and converted to the required `{name, url, test_type}` shape.

## Conversation Policy

The agent supports four behaviors. Vague requests such as “I need an assessment” return no recommendations and ask a focused clarification question. Once the user provides role or assessment-type context, the agent returns a shortlist. If the user changes constraints mid-conversation, the full message history is rescored, so refinements such as “actually add personality tests” update the shortlist. Comparison requests such as “OPQ vs GSA” retrieve both catalog records and compare only the stored descriptions and test types.

Guardrails reject off-topic requests, legal/salary/interview-advice questions, and prompt-injection attempts. Refusals keep `recommendations` empty and redirect the user back to SHL assessment selection.

## Evaluation

I added tests for health, schema-safe vague clarification, Java developer recommendations, refinement with personality tests, OPQ/GSA comparison, off-topic refusal, and prompt-injection refusal. `scripts/evaluate_public_traces.py` can replay JSON traces and report catalog URL validity plus Recall@10 against expected names.

What did not work well: relying on a fully generative LLM would risk non-catalog URLs and inconsistent schemas. Live scraping is also brittle because the public SHL product-catalog route can redirect to a general products page, so the deployed service uses the local snapshot. Asking too many clarification questions is risky because the evaluator has an 8-turn cap, so the policy asks only one targeted question and recommends as soon as role plus useful constraints are present.
