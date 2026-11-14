# How this project was built

This folder records the work done **before and around** the code, in the
order a Forward Deployed Engineer would do it on a client engagement. Each
document answers one question; read them in order.

| Step | Document | Question it answers |
|---|---|---|
| 1. Discovery | [00_problem_brief.md](00_problem_brief.md) | Who is the user, what do they really need, what constrains us? |
| 2. Rationalisation | [01_delegation_plan.md](01_delegation_plan.md) | Which parts are deterministic code, which need an LLM, who checks what? |
| 3. Requirement | [02_product_requirement.md](02_product_requirement.md) | What exactly counts as success, in measurable terms? |
| 4. Design | [03_technical_spec.md](03_technical_spec.md) | What is built, how the parts talk to each other |
| 5. Definition of done | [04_acceptance_tests.md](04_acceptance_tests.md) | Which automated test proves each requirement |
| 6. Decisions | [05_decision_log.md](05_decision_log.md) | Why each choice was made, and every assumption to recalibrate |
| 7. Build | [06_build_prompt.md](06_build_prompt.md) | The instructions used to turn the spec into code with an AI assistant |
| 8. Ownership | [07_author_review.md](07_author_review.md) | What the author checked personally before signing the work |

The code was written with an AI assistant (Claude), from requirements and
corrections set by the author. The split of responsibilities is explicit in
the delegation plan; the author's own review is tracked in step 8.
