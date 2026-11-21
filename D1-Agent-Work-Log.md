# Deliverable 1 agent work log

Token counts come from the Lab 6 meter. Costs use the rates configured at run time. The Gemini runs below used free-tier rates of $0 per million input and output tokens.

| Date | Requirement / task | Tool and model | Request | Result and review | Input tokens | Output tokens | Cost | Lesson |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | --- |
| 2026-11-21 | AH-R01 / AH-T01 | Lab 6 in Docker, Gemini 3.1 Flash-Lite | Implement the single-day request service in `after_hours.py` with SQLite and run the provided acceptance test. | Accepted as generated. The first test run failed as expected. The operator approved the write to `after_hours.py`. Lab 6 finished with tests passing after 7 steps and 7 model calls. The acceptance test was unchanged and passed again after the implementation was copied into the repository. | 13,646 | 635 | $0.00 | Give the agent the test and the service contract up front. One earlier attempt stalled after spending two calls locating and reading the test. |
| 2026-11-21 | AH-R02 / AH-T02 | Lab 6 in Docker, Gemini 3.1 Flash-Lite | Validate single-day requests in the service before saving them and run the acceptance checks. | Accepted as generated for the tested cases. All four validation cases failed before the run. Lab 6 finished after 9 steps and 9 calls. The test file was unchanged, and all five cases passed after copying the implementation into the repository. | 27,461 | 1,776 | $0.00 | Check error behavior and database state together. Passing the service checks gives us a contract for displaying field errors when the form is built. |

## Setup and interrupted runs

- The read-only smoke test completed in 2 calls with 1,707 input tokens, 306 output tokens, and $0.00 at configured rates. It established that Lab 6 could read the specs through Gemini. It is excluded from the five substantive measured tasks.
- The first AH-T01 implementation attempt stopped at Docker DNS resolution before Gemini returned any usage. A later attempt read the test and timed out on request 3 before writing code. The launcher did not print a token total for that interrupted run.
- The successful run covers the AH-T01 service check. The browser form and authenticated submission flow are still pending for the vertical slice.
