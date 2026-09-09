# Farmer Products Shopping Cart — Final Project Outline

Status: finalized planning baseline; public catalog implementation is in progress.

Based on the supplied **Fast API Assessment -(1).pdf**, the original project outline, and the agreed review corrections. Refresh-token rotation is included in the implementation scope. Future enhancements are explicitly separated from delivery commitments.

## 1. Objective and scope

Build a clean, explainable full-stack shopping-cart application using React, FastAPI, and PostgreSQL. Deliver all assessment functionality, demonstrate correctness under realistic failure conditions, and develop enough understanding to explain and modify the implementation during a mid-to-senior interview.

The project will be built incrementally with LLM assistance: understand each decision, implement a small coherent slice, inspect the code and SQL, verify the behavior, and make a genuine milestone commit. Avoid unexplained generated scaffolding and unnecessary abstraction.

**Timeline ambiguity:** the PDF says “Duration: 2Hours” on page 1 and submission within two days on page 4. This outline describes the agreed take-home scope; it is not a promise that all learning and implementation fits two hours. Confirm the evaluator's intended time budget before estimating delivery.

## 2. Requirement traceability

| Brief requirement | Planned implementation |
| --- | --- |
| Secure admin login | Seeded admin, password hashing, short-lived JWT access tokens, rotating refresh tokens |
| Add/edit/delete products | Admin product forms and protected APIs; soft deletion |
| View all products as admin | Admin listing includes active and inactive, excludes deleted products |
| Activate/deactivate | Explicit admin status action |
| Update available stock | Dedicated stock action with concurrency protection |
| Eight product fields | Name, category, farmer name, description, price, available quantity, image URL, active/inactive status |
| Customer product listing/details | Public APIs expose only active, non-deleted products |
| Search by name/filter by category | Combined, parameterized filters with pagination |
| Add/update/remove/view cart | Persistent guest cart with ownership checks |
| Checkout | Transactional order placement, stock decrement, immutable order snapshots, confirmation |
| View Orders API | Admin-only order listing; compact orders page included as a useful addition |
| Stock never negative | Application checks, concurrency-safe writes, database constraint |
| Automatic grand total | Server-side Decimal calculation |
| Form validation | Frontend feedback, API validation, business rules, database constraints |
| React requirements | Functional components, hooks, React Router, Axios |
| Responsive UI | Mobile and desktop layouts, accessible forms, explicit UI states |
| Relational database | PostgreSQL with foreign keys, constraints, and Alembic migrations |
| Deliverables | GitHub repository, README, migration scripts, environment examples; optional screenshots |

## 3. Chosen architecture and stack

One React application serves the admin and customer experiences. One FastAPI application owns authentication, catalog, carts, and orders. One PostgreSQL database stores application state. This is a modular monolith.

| Area | Choice and purpose |
| --- | --- |
| Frontend | React + TypeScript + Vite |
| Navigation | React Router |
| HTTP | Axios with one shared client and controlled refresh handling |
| State | Local component state and focused contexts/hooks; server responses remain authoritative |
| Backend | Python + FastAPI |
| Contracts | Separate Pydantic request/response schemas |
| Persistence | SQLAlchemy async with a compatible PostgreSQL driver |
| Schema evolution | Alembic migrations |
| Configuration | Environment variables and pydantic-settings |
| Tests | Focused unit tests plus PostgreSQL integration tests; selected frontend interaction tests |
| Local setup | Documented native setup; Docker Compose as a convenience if time permits |

Backend responsibilities: route modules may query through the injected session directly when the operation is simple, as in public catalog reads. Extract a service only when business rules or transaction boundaries justify it, especially refresh rotation and checkout. Models describe storage and Pydantic schemas describe the API contract. Avoid generic repositories, base services, and one-use wrapper classes.

Complexity must be earned by working functionality. Start with a small number of plainly named files, keep code close to where it is used, and extract it only when reuse, file size, or a real business workflow creates a clear need. Do not create future models, configuration, modules, or database tables before their feature is implemented.

Async is an I/O-concurrency choice, not a guarantee of faster queries or thread safety. Keep blocking work out of the event loop and do not share a database session across concurrent tasks. During implementation, inspect the SQL generated by the ORM and explain the underlying PostgreSQL behavior.

## 4. Product and business assumptions

- Customers shop as guests; there is no customer registration or farmer login.
- One admin permission level; no public admin-registration endpoint.
- Categories are seeded and selected from a list. Category-management UI is outside scope.
- Product images use validated HTTP/HTTPS URLs. Provide an image fallback; the backend does not fetch arbitrary image URLs.
- Use one documented currency, initially INR, with two decimal places. Represent monetary API values as decimal strings and format them for display; do authoritative arithmetic on the server.
- Quantities are positive integer sale units. Describe the unit in the product name/description, such as “Tomatoes — 1 kg pack.” Fractional-weight ordering is outside scope.
- Product price must be positive; available stock may be zero.
- Active products with zero stock remain visible with an “Out of stock” label and disabled purchase action. This is the documented interpretation of available products.
- Deactivation hides a product from public catalog/detail APIs. Soft deletion removes it from normal admin and customer lists while preserving historical relationships.
- Adding to a cart reserves neither inventory nor price.
- Checkout means placing a confirmed order. No payment gateway, tax, shipping, discounts, pending-payment state, cancellation, or refunds.

## 5. Authentication with refresh-token rotation — included

### Token and session design

- Hash passwords with a maintained Argon2 implementation. Seed the initial admin through an explicit command using supplied credentials; never commit real credentials.
- Access token: signed JWT with validated expiry, issuer, audience, subject, and an allowed algorithm. Keep it in frontend memory, not persistent browser storage.
- Refresh token: cryptographically random opaque secret in an HttpOnly cookie. Store only its digest in PostgreSQL.
- Initial configurable lifetimes: access token 15 minutes; refresh session absolute lifetime seven days. Rotation does not extend that absolute deadline.
- A login creates a refresh session/family. Each successful refresh consumes the previous token and issues a replacement plus a new access token.
- Retain consumed-token records until the family expires so reuse can be detected. A database transaction serializes rotation for a family.
- If a previously consumed token is presented, revoke that family and require login. Do not issue another replacement. Rotation and family invalidation follow the replay-detection principle described in [RFC 9700, section 4.14](https://www.rfc-editor.org/rfc/rfc9700.html#section-4.14); this application is not claiming to implement a complete OAuth authorization server.

### Cookie and request protections

- Production cookies use Secure, HttpOnly, a suitable SameSite setting, and a constrained path. Refresh cookies use the authentication path; guest identity cookies use the cart/order paths or a shared API prefix as needed.
- Prefer same-site frontend/API deployment. Document separate development origins and cookie settings explicitly.
- Protect cookie-authenticated state changes with an allowed-Origin check and a session-bound CSRF token sent in a custom header. SameSite is defense in depth; CORS is not authorization or a complete CSRF defense. Protect login/session bootstrap against cross-origin abuse as well. See [OWASP CSRF guidance](https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html).
- Return tokens only through the intended channel; never log passwords, tokens, cookies, or authorization headers.

### Frontend lifecycle and failure behavior

- On page reload, attempt one refresh to restore the admin session before deciding whether a protected route should redirect.
- On an eligible access-token expiry response, allow one in-flight refresh per browser tab; queue other failed requests behind it, then retry each request at most once.
- Never recursively refresh a failed refresh request. Network failures and permission-denied responses must not trigger unlimited refresh loops.
- Coordinate refresh across supported browser tabs through a cross-tab lock; notify tabs about logout/session changes. Strict reuse detection can force re-login if competing refresh requests escape coordination.
- A lost refresh response can also require re-login because the old token is already consumed. Document this bounded trade-off rather than silently accepting token replay.
- Logout revokes the current refresh family, clears the cookie and in-memory access token, and updates the UI. Already-issued stateless access tokens remain valid until their short expiry; immediate access-token revocation is not claimed.
- Expired/revoked sessions return a clear unauthorized response. Enforce admin authorization on every protected backend route, regardless of UI guards.

## 6. Database design

| Table | Important fields and rules |
| --- | --- |
| users | id, normalized unique email, password_hash, role, created_at |
| refresh_sessions | id, user_id FK, absolute_expires_at, revoked_at, created_at |
| refresh_tokens | id, session_id FK, unique token_digest, consumed_at, expires_at, replacement_token_id nullable, created_at |
| categories | id, unique name |
| products | id, name, category_id FK, farmer_name, description, Numeric price, integer available_quantity, image_url, status, is_deleted, version, timestamps |
| guest_sessions | id, unique token_digest, expires_at, created_at; supports persistent cart ownership and order-result access |
| carts | id, guest_session_id FK, state (open/converted), version, timestamps |
| cart_items | id, cart_id FK, product_id FK, quantity; unique(cart_id, product_id) |
| orders | id, unique cart_id FK, guest_session_id FK, status=confirmed, currency, grand_total, idempotency_key, request_fingerprint, created_at |
| order_items | id, order_id FK, product_id FK, product_name_snapshot, unit_price_snapshot, quantity |

This table is the target design, not the contents of the first migration. Migrations are incremental: the catalog iteration creates only categories and products; authentication adds its user and token tables; cart and checkout add their own tables when those behaviors are built.

Constraints: product price > 0; stock >= 0; cart/order quantities > 0; order prices > 0; non-null required fields; foreign keys; unique token digests; unique checkout key within a guest session. Enforce at most one open cart per guest with a partial unique index. Keep converted carts so each order remains linked to its source basket; create a new open cart when shopping resumes.

Use relevant FK/lookup indexes, including product category, cart items by cart, order items by order, and token digest lookups. Unique constraints already supply their corresponding indexes; do not duplicate them. Choose order-list indexing to match its sorting query. Trigram indexing is deferred to section 14.

Use timezone-aware timestamps. Restrict destructive cascades that would erase order history. No cart price snapshot is authoritative; purchase-time snapshots belong in order_items.

## 7. API contract outline

Paths below are relative to the chosen API prefix. Public and admin product reads are deliberately separate.

| Access | Method and path | Purpose |
| --- | --- | --- |
| Public/auth | POST /auth/login | Authenticate admin and create refresh family |
| Cookie protected | POST /auth/refresh | Rotate refresh token and issue access token |
| Cookie protected | POST /auth/logout | Revoke current refresh family |
| Session bootstrap | GET /auth/csrf | Obtain session-bound CSRF material through an allowed origin |
| Public | GET /categories | Category dropdown options |
| Public | GET /products | Active, non-deleted list; search/category/page/page_size |
| Public | GET /products/{id} | Purchasable catalog detail; hidden products return 404 |
| Admin | GET /admin/products | Active and inactive product list |
| Admin | GET /admin/products/{id} | Load edit form, including inactive product |
| Admin | POST /admin/products | Create product |
| Admin | PATCH /admin/products/{id} | Edit supplied descriptive/price fields only |
| Admin | DELETE /admin/products/{id} | Soft delete |
| Admin | PATCH /admin/products/{id}/status | Activate/deactivate |
| Admin | PATCH /admin/products/{id}/stock | Set stock using expected product version |
| Guest bootstrap | POST /guest-session | Establish opaque guest cookie and CSRF material |
| Guest | GET /cart | Current cart, current prices, totals, availability issues |
| Guest | POST /cart/items | Add quantity to an existing or new product line |
| Guest | PATCH /cart/items/{item_id} | Set a line's absolute quantity |
| Guest | DELETE /cart/items/{item_id} | Remove owned line |
| Guest | POST /orders/checkout | Place order with idempotency key and reviewed cart expectations |
| Guest | GET /orders/{id} | Retrieve own confirmation; verify guest ownership |
| Admin | GET /admin/orders | Required View Orders API |
| Admin | GET /admin/orders/{id} | Read purchased items for order inspection |

Document request/response examples in FastAPI's generated API documentation. Use consistent structured errors with a stable code, readable message, and relevant field/item details. Distinguish authentication failure (401), authorization failure (403), hidden/missing resource (404), business conflict (409), and input validation (422). Return 201 for newly created resources; a successful checkout replay may return 200 with the original order.

Search is case-insensitive literal substring matching. Parameterize values and escape LIKE wildcard characters when treating the input literally. Apply search and category together; reset pagination when filters change; use deterministic sorting and a capped page size.

## 8. Cart, pricing, and stock correctness

### Ownership and mutations

Resolve the cart from the guest cookie, never from an arbitrary customer ID accepted in the request body. Check ownership for every item operation and order read. Repeated add increments the existing line and validates the resulting quantity. Reject non-integers, non-positive quantities, inactive/deleted products, and quantities exceeding current stock.

Serialize mutations for the same cart using its database row lock, and increment its version. Checkout follows the same locking protocol so a concurrent quantity change cannot silently alter the reviewed purchase.

If a product becomes inactive/deleted, return a minimal unavailable-line indicator so it can be removed; do not expose it as an active catalog product. If stock falls below the selected quantity, show a clear conflict and allow correction.

### Price policy

GET /cart computes current line totals and grand total on the server. The checkout request includes the reviewed cart version and expected line prices as comparison data only. Validate these against authoritative database values. If prices or cart contents changed, return a conflict with refreshed review data and require confirmation. Never use client prices or totals to calculate the order.

### Transactional checkout

1. Resolve guest identity and validate the idempotency key/request fingerprint. Matching completed retries return the existing order, even after the source cart is converted.
2. Start one transaction and lock the source cart. Recheck replay state after acquiring the lock; verify ownership, open state, non-empty contents, and expected cart version.
3. Process products in ascending ID order. Perform conditional stock decrements requiring sufficient stock, active status, and non-deleted state. Use returned authoritative product fields for pricing/name snapshots; compare reviewed prices and roll back on mismatch.
4. If any item fails, roll back the entire transaction. Return the conflict after rollback, with refreshed information as appropriate.
5. Calculate Decimal totals, create the order and item snapshots, record the idempotency key/fingerprint, and mark the cart converted.
6. Commit once. Only then report success. The converted cart is no longer the active basket, so the UI shows an empty shopping cart and the confirmation.

The unique order/cart relationship and cart lock prevent two conversions of the same basket, even with different keys. A matching key must not silently apply to a different request. Do not implement checkout through a collection of independently committed repository operations.

**Locking explanation:** conditional UPDATE combines the stock check and decrement; it still takes row locks until transaction end. SELECT FOR UPDATE is another valid implementation choice, not an inherently inferior strategy. Consistent lock order reduces deadlock risk; rollback and a clear retry path handle aborted transactions. See [PostgreSQL explicit locking](https://www.postgresql.org/docs/current/explicit-locking.html).

**Admin stock edits:** use an expected product version when setting an absolute stock count. Checkout and product writes increment that version. A stale admin stock submission receives a conflict and reloads current data. Descriptive edits never include stock implicitly. This avoids overwriting stock sold since a form was opened.

## 9. Frontend pages and behavior

| Area | Pages and actions |
| --- | --- |
| Admin | Login, product list, add product, edit product, orders list/detail |
| Customer | Product listing, product details, shopping cart, checkout review/confirmation |

Use one shared product form for add/edit. Keep stock/status actions explicit. Include deletion confirmation. Product forms expose all assessment fields.

Provide loading indicators, empty catalogs/carts, no-search-results messages, inline validation, request errors, expired-session handling, stock/price conflicts, and success confirmation. Disable duplicate submissions while pending without treating that as the server's correctness mechanism.

Debounce search by approximately 300 ms; cancel or ignore stale responses. Use labeled inputs, keyboard-accessible controls, meaningful image alt text, visible focus, and layouts usable on mobile and desktop. Prefer authoritative mutation responses/refetching over optimistic inventory changes in this small application.

Current frontend organization keeps `api.ts`, `AppLayout.tsx`, and `currency.ts` at the source root, with only `pages/` and `components/` folders. The backend keeps configuration, database setup, models, and schemas as single files, with route modules under `api/`. Split files or add custom hooks/services only when reuse, file size, or a substantial workflow makes the benefit concrete. Refresh rotation and checkout are likely service candidates because they own multi-step transactions; ordinary CRUD is not automatically one.

## 10. Validation and security baseline

- Frontend checks improve feedback; backend validation and database constraints enforce correctness.
- Trim required strings; cap lengths, page sizes, and quantities; reject invalid categories, prices, URLs, and states.
- Use parameterized queries, including any handwritten SQL. ORM use does not make interpolated raw SQL safe.
- Use response schemas to exclude credential/session fields and administrative data from public responses.
- Apply explicit CORS origins, cookie/CSRF protections, and secret configuration.
- Include basic login/refresh throttling for the single-process assessment environment. Document that process-local counters do not provide deployment-wide enforcement.
- Log request IDs, routes, status, and relevant failures without credentials or tokens. Return generic server errors to clients while retaining diagnostic details in server logs.

## 11. Acceptance tests and technical evidence

| Scenario | Expected outcome |
| --- | --- |
| Unauthorized direct admin API call | Rejected even if UI routing is bypassed |
| Successful refresh | Old token consumed, replacement issued, access restored |
| Replay consumed refresh token | Family revoked; login required |
| Concurrent refresh attempts | At most one rotation succeeds; strict replay policy is exercised |
| Logout/expired refresh | Refresh cannot restore the session |
| Missing/invalid CSRF on cookie mutation | Request rejected |
| Customer A targets customer B's cart item/order | No access or mutation |
| Duplicate add or invalid quantity | One line per product; resulting quantity checked |
| Inactive/deleted detail and stale cart | Hidden detail; checkout blocked for unavailable item |
| Price changed after review | Conflict and reconfirmation; no unintended order/stock change |
| Two guests buy the last unit | Only one purchase succeeds; stock is zero |
| One item fails in a multi-item checkout | No partial stock decrement or order remains |
| Checkout retried after success/lost response | Original order returned; stock unchanged |
| Same cart submitted with different keys | At most one order created |
| Cart edit races checkout | Serialized behavior or version conflict |
| Admin stock form is stale | Conflict rather than overwriting newer inventory |
| Product edited/deleted after purchase | Historical order names/prices remain unchanged |
| Search responses arrive out of order | UI retains the latest query's results |

Use real PostgreSQL and separate connections/transactions for concurrency tests; mocks or SQLite do not establish PostgreSQL locking behavior. Unit-test calculations and validation where useful. Test high-risk workflows as they are built, then run a final clean-setup and browser smoke check. Avoid chasing arbitrary coverage percentages.

## 12. Delivery checklist

- [ ] GitHub repository with meaningful incremental commits reflecting actual work.
- [ ] Complete required admin/customer flows and View Orders API.
- [ ] Alembic migrations and repeatable admin/category/sample-product setup.
- [ ] Backend/frontend environment examples; no secrets committed.
- [ ] README with overview, stack, prerequisites, backend/frontend/database setup, run steps, assumptions, test commands, and demo flow.
- [ ] README explanation of token rotation, checkout atomicity, price policy, guest ownership, and known limitations.
- [ ] Dependency versions captured so setup is reproducible.
- [ ] Optional Docker Compose and screenshots if time permits.

The brief accepts migrations OR a SQL script. Alembic is the chosen schema source; a separately maintained duplicate schema.sql is unnecessary. Hosting/deployment is not required by the supplied brief.

## 13. Step-by-step build and explanation plan

| Stage | Build outcome | Explanation checkpoint |
| --- | --- | --- |
| 1 | Scope, assumptions, API contracts, acceptance cases | Why each feature belongs; how success is measured |
| 2 | Project setup and catalog-only first migration | HTTP boundaries, current relationships, constraints, dependency/session lifetime |
| 3 | Public catalog through DB/API/UI | Query construction, response models, fetching, search/filter, pagination |
| 4 | Admin auth with rotation and product management | JWT vs refresh session, replay detection, CSRF, authorization, safe edits |
| 5 | Guest cart | Identity, ownership, uniqueness, stock checks, server state |
| 6 | Checkout and confirmation | Transactions, locks, idempotency, Decimal, stale data, rollback |
| 7 | Orders, accessibility, responsive UI, error states | Historical records, UX behavior under failures |
| 8 | Final verification, documentation, interview rehearsal | Evidence, trade-offs, limitations, justified future work |

Each stage follows: explain the behavior and concepts; implement a small vertical slice; trace a request through React, FastAPI, and SQL; verify representative success/failure cases; review the code; make a real commit. Include interview questions and debugging exercises at each stage. The learner can defer answering exercises while continuing the roadmap.

## 14. Future enhancements — conditional, not delivery commitments

These are narrowly related to existing requirements. None is necessary merely because the project is described as mid-to-senior. Implement only when the stated trigger is demonstrated. No additional business features are proposed.

### 14.1 Trigram index for product-name substring search

**Trigger:** representative catalog size and query measurements show substring search exceeding the agreed latency target.

**Current baseline:** parameterized ILIKE contains search, debounce, and bounded result pages. An ordinary B-tree on name generally does not help a leading-wildcard contains predicate.

**Proposed change:** enable PostgreSQL pg_trgm and add a GIN index using gin_trgm_ops on product name. Consider a partial index restricted to active, non-deleted products only if measured public-search queries justify it; such an index would not cover unrestricted admin search.

**Verification:** compare EXPLAIN (ANALYZE, BUFFERS), latency, and index size on representative data. Patterns with no extractable trigrams can degrade to a full-index scan; tiny catalogs or very short inputs may see little benefit. Account for write/storage cost. Preserve substring behavior; typo tolerance or ranked fuzzy search would be a separate product decision. See [PostgreSQL pg_trgm](https://www.postgresql.org/docs/current/pgtrgm.html).

**Interview explanation:** “I kept substring search simple for the assessment. If measurements show it becoming slow, I would evaluate a trigram GIN index and verify the query plan and write overhead before adopting it.”

### 14.2 Shared throttling when deploying multiple processes

**Trigger:** public deployment or multiple API workers/instances make process-local login/refresh limits insufficient.

**Proposed change:** enforce limits at a shared gateway or shared atomic counter store, with expiry and carefully chosen account/IP keys. Do not add Redis solely for this assessment. Keep generic authentication errors and avoid simplistic account lockouts that allow denial of service.

**Verification:** requests spread across workers obey the same budget; expiry, proxy/IP handling, and limiter failure behavior are tested.

**Interview explanation:** “The assessment limiter is local. Before exposing multiple workers publicly, I would move enforcement to a shared boundary so increasing worker count does not multiply the allowed attempts.”

### 14.3 Retention cleanup for long-running operation

**Trigger:** guest carts and refresh-token records accumulate during sustained use.

**Proposed change:** scheduled, batched cleanup of expired guest state and expired refresh families. Keep consumed tokens until their family's replay-detection window closes. Preserve orders and source-cart relationships; define guest ownership retention or anonymization deliberately rather than cascading away order data.

**Verification:** active sessions remain valid, replay detection still works within the defined lifetime, and order history is preserved. Add supporting expiry indexes only where cleanup query plans warrant them.

**Interview explanation:** “Expiry checks already reject old sessions. Cleanup is separate operational maintenance to control storage growth, with retention rules that preserve purchase history.”

No planned microservices, queues, caches for inventory, replicas, partitioning, or search service. Correctness, bounded queries, and measurement come first.

## 15. Interview walkthrough

Demonstrate the catalog; log in as admin; create/edit/deactivate a product; add items as a guest; change quantity; show a validation failure; checkout; inspect the order and resulting stock. Then trace one normal request and one concurrent checkout through the system.

Be prepared to explain:

1. Why this modular monolith and stack fit the assessment.
2. Authentication vs authorization; access vs refresh tokens; rotation, reuse detection, and logout limitations.
3. Guest identity and object-level ownership checks.
4. API schemas vs database models; frontend feedback vs authoritative validation.
5. Money representation, live cart pricing, and immutable order snapshots.
6. Check-then-write races, row locks, transaction boundaries, and rollback.
7. Idempotency vs disabled buttons, and why cart mutation must coordinate with checkout.
8. Why async does not solve database races or guarantee performance.
9. Which tests prove the difficult behavior and which limitations remain.
10. Why trigram indexing and the other operational enhancements are conditional rather than already implemented.

The goal is to explain code actually built and verified, distinguish implemented behavior from future ideas, and make trade-offs confidently without claiming production guarantees that the project has not established.
