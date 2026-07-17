# Backend Engineering Knowledge Base

## API Design
RESTful API design emphasizes resource-oriented URLs, correct use of HTTP verbs (GET, POST,
PUT, PATCH, DELETE), and meaningful status codes (200, 201, 204, 400, 401, 403, 404, 409, 422,
500). Idempotency matters for PUT and DELETE: repeated calls should not change the result beyond
the first successful call. Versioning strategies include URL versioning (/v1/), header
versioning (Accept: application/vnd.api+json;version=2), and content negotiation. Pagination
approaches include offset-based (?page=2&limit=20) and cursor-based pagination, the latter being
more stable under concurrent writes. GraphQL is an alternative that lets clients specify exactly
the fields they need, avoiding over-fetching and under-fetching, at the cost of more complex
caching and potential N+1 query problems that require dataloaders to batch resolution.

## Databases and Data Modeling
Relational databases (PostgreSQL, MySQL) enforce ACID guarantees: Atomicity, Consistency,
Isolation, Durability. Normalization (1NF-3NF) reduces redundancy but can require joins;
denormalization trades storage for read performance. Indexing strategies include B-tree indexes
for range queries and equality lookups, hash indexes for pure equality, and GIN/GiST indexes in
Postgres for full-text search or JSONB. Isolation levels (Read Committed, Repeatable Read,
Serializable) trade consistency for concurrency; phenomena to understand include dirty reads,
non-repeatable reads, and phantom reads. NoSQL databases (MongoDB, Cassandra, DynamoDB) trade
some consistency guarantees for horizontal scalability, often following the CAP theorem: under a
network partition, a system must choose between Consistency and Availability. Cassandra favors
AP with tunable consistency levels; traditional RDBMS favor CP or single-node CA.

## Caching
Caching layers (Redis, Memcached) reduce load on primary databases. Cache invalidation strategies
include TTL expiry, write-through, write-behind, and cache-aside (lazy loading). Cache stampede
(thundering herd) occurs when many requests miss the cache simultaneously after expiry; mitigated
with request coalescing, jittered TTLs, or probabilistic early expiration. Distributed caches
need consideration of eviction policies (LRU, LFU) and consistency across replicas.

## Concurrency and Asynchronous Processing
Backend systems handle concurrency via multi-threading, multi-processing, or asynchronous
event loops (asyncio in Python, epoll-based event loops in Node.js). Race conditions arise when
shared mutable state is accessed without proper synchronization (locks, mutexes, semaphores,
optimistic locking with version numbers). Message queues (RabbitMQ, Kafka, SQS) decouple
producers from consumers, enabling asynchronous processing, retries with backoff, dead-letter
queues, and at-least-once vs exactly-once delivery semantics. Kafka's log-based architecture with
partitions enables high-throughput ordered processing per partition and consumer group
rebalancing for scalability.

## Authentication and Authorization
Authentication verifies identity (who you are); authorization determines permissions (what you
can do). Common mechanisms include session cookies with server-side state, JWTs (stateless,
signed tokens carrying claims, vulnerable to revocation challenges unless a blocklist or short
expiry is used), OAuth2 (authorization code flow, client credentials flow, PKCE for public
clients), and OpenID Connect layered on top of OAuth2 for identity. Role-Based Access Control
(RBAC) assigns permissions to roles; Attribute-Based Access Control (ABAC) evaluates policies
against user/resource/environment attributes for finer-grained control.

## System Design and Scalability
Horizontal scaling adds more machines; vertical scaling adds more resources to one machine.
Load balancers (round robin, least connections, consistent hashing) distribute traffic across
instances. Database read replicas offload read traffic; sharding partitions data across nodes by
a shard key, requiring careful key selection to avoid hot shards. Rate limiting algorithms include
token bucket, leaky bucket, and sliding window counters, used to protect services from abuse.
Circuit breakers (open, half-open, closed states) prevent cascading failures when a downstream
dependency is unhealthy. Idempotency keys let clients safely retry non-idempotent operations like
payments.

## Testing and Reliability
Unit tests validate isolated logic; integration tests validate interactions between components
(e.g., database, external APIs); contract tests validate API compatibility between services.
Observability rests on three pillars: logs (discrete events), metrics (aggregated numeric time
series, e.g. via Prometheus), and traces (distributed request paths, e.g. via OpenTelemetry).
SLIs, SLOs, and SLAs quantify reliability targets and the consequences of missing them. Graceful
degradation and bulkheading (isolating failures to one part of a system) improve resilience.

## Security Fundamentals
Input validation and parameterized queries prevent SQL injection. Output encoding prevents XSS.
CSRF tokens protect state-changing requests from cross-site forgery. Secrets should never be
hardcoded; they belong in environment variables or secret managers (Vault, AWS Secrets Manager).
TLS terminates encryption in transit; hashing algorithms like bcrypt or argon2 (not plain SHA256)
should be used for password storage due to their deliberate slowness and salting.
