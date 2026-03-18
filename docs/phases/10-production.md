# Phase 10: Production Hardening

## Meta

| Field | Value |
|-------|-------|
| **Goal** | Kubernetes deployment, gVisor sandbox, observability, autoscaling, security hardening |
| **Prerequisites** | Phase 09 (billing, marketplace — all features complete) |
| **Effort** | 4-5 days |
| **Key Technologies** | Kubernetes, Kustomize, gVisor, OpenTelemetry, Grafana, Prometheus, Loki, Tempo |

---

## Context

This is the final phase — hardening the platform for production deployment. Everything built in Phases 01-09 works in Docker Compose for development. This phase adds:

1. **Kubernetes manifests** — Kustomize base + overlays for dev/staging/prod
2. **gVisor sandbox upgrade** — Replace Docker containers with gVisor (runsc) for stronger isolation
3. **Observability stack** — OpenTelemetry + Grafana (traces, metrics, logs)
4. **Autoscaling** — HPA for API/MCP gateway, custom autoscaler for sandbox pool
5. **Security hardening** — TLS everywhere, secrets management, vulnerability scanning
6. **Performance targets** — Validate non-functional requirements

### Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                        │
│                                                                  │
│  Ingress (Traefik) — TLS, Rate Limiting                          │
│       │                                                          │
│  ┌────▼────────────┐  ┌────────────────┐  ┌─────────────────┐  │
│  │  API Deployment  │  │  MCP Gateway   │  │  Frontend       │  │
│  │  3-10 pods (HPA) │  │  2-5 pods (HPA)│  │  2 pods         │  │
│  └─────────────────┘  └────────────────┘  └─────────────────┘  │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Sandbox Pool (StatefulSet) — 5-20 pods, gVisor runtime   │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Data: PostgreSQL (CloudNativePG) · Redis · MinIO/S3      │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Observability: OTel Collector · Grafana · Loki · Tempo   │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

No new tables. This phase is infrastructure-only.

---

## API Endpoints

No new endpoints. Existing endpoints get instrumented with OpenTelemetry.

---

## Implementation Steps

### Step 1: Kubernetes Base Manifests (Kustomize)

**Directory**: `infra/k8s/base/`

**File**: `infra/k8s/base/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml
  - api-deployment.yaml
  - api-service.yaml
  - mcp-gateway-deployment.yaml
  - mcp-gateway-service.yaml
  - frontend-deployment.yaml
  - frontend-service.yaml
  - sandbox-statefulset.yaml
  - ingress.yaml
```

**File**: `infra/k8s/base/api-deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: yoagent-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: yoagent-api
  template:
    metadata:
      labels:
        app: yoagent-api
    spec:
      containers:
        - name: api
          image: yoagent/api:latest
          ports:
            - containerPort: 8000
          resources:
            requests:
              cpu: "500m"
              memory: "1Gi"
            limits:
              cpu: "1"
              memory: "2Gi"
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: yoagent-secrets
                  key: database-url
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: yoagent-secrets
                  key: redis-url
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 30
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
```

**File**: `infra/k8s/base/sandbox-statefulset.yaml`

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: yoagent-sandbox
spec:
  replicas: 5
  selector:
    matchLabels:
      app: yoagent-sandbox
  template:
    metadata:
      labels:
        app: yoagent-sandbox
    spec:
      runtimeClassName: gvisor  # Uses gVisor runtime
      containers:
        - name: sandbox
          image: yoagent/sandbox:latest
          ports:
            - containerPort: 8200
          resources:
            requests:
              cpu: "1"
              memory: "2Gi"
            limits:
              cpu: "2"
              memory: "4Gi"
          securityContext:
            privileged: false
            readOnlyRootFilesystem: true
          volumeMounts:
            - name: uv-cache
              mountPath: /shared/uv-cache
      volumes:
        - name: uv-cache
          persistentVolumeClaim:
            claimName: uv-cache-pvc
```

### Step 2: Kustomize Overlays

**File**: `infra/k8s/overlays/dev/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
bases:
  - ../../base
patchesStrategicMerge:
  - api-patch.yaml    # replicas: 1, lower resources
```

**File**: `infra/k8s/overlays/prod/kustomization.yaml`

```yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
bases:
  - ../../base
patchesStrategicMerge:
  - api-patch.yaml    # replicas: 3, HPA, higher resources
  - hpa.yaml
```

### Step 3: Horizontal Pod Autoscaling

**File**: `infra/k8s/overlays/prod/hpa.yaml`

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: yoagent-api-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: yoagent-api
  minReplicas: 3
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Pods
      pods:
        metric:
          name: http_requests_per_second
        target:
          type: AverageValue
          averageValue: "500"
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: yoagent-mcp-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: yoagent-mcp-gateway
  minReplicas: 2
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

### Step 4: gVisor Sandbox Upgrade

**File**: `backend/app/runtime/sandbox/manager.py` (modify for gVisor)

```python
class SandboxManager:
    def __init__(self, runtime: str = "runsc"):
        self.runtime = runtime

    async def execute(self, code: str, config: SandboxConfig | None = None) -> ExecutionResult:
        config = config or SandboxConfig()
        container_name = f"sandbox-{uuid.uuid4().hex[:12]}"

        cmd = [
            "docker", "run", "--rm",
            "--runtime", self.runtime,  # gVisor runtime
            "--name", container_name,
            "--memory", f"{config.max_memory_mb}m",
            "--cpus", "1",
            "--network", "none" if not config.network_access else "bridge",
            "--pids-limit", "10",
            "--read-only",
            "--tmpfs", "/tmp:size=100m",
            "--tmpfs", "/workspace:size=100m",
            "-w", "/workspace",
            self.image,
            "python", "-c", code,
        ]
        # ... rest same as Phase 05
```

### Step 5: OpenTelemetry Integration

**File**: `backend/app/core/telemetry.py`

```python
from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor

def setup_telemetry(app):
    """Initialize OpenTelemetry instrumentation."""
    # Tracer
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=settings.OTEL_ENDPOINT))
    )
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    meter_provider = MeterProvider(
        metric_readers=[PeriodicExportingMetricReader(
            OTLPMetricExporter(endpoint=settings.OTEL_ENDPOINT),
            export_interval_millis=30000,
        )]
    )
    metrics.set_meter_provider(meter_provider)

    # Auto-instrumentation
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=engine)
    RedisInstrumentor().instrument()
```

### Step 6: Custom Metrics

**File**: `backend/app/core/telemetry.py` (extend)

```python
meter = metrics.get_meter("yoagent")

# Custom metrics
agent_run_counter = meter.create_counter(
    "yoagent.agent.runs",
    description="Number of agent runs",
)
agent_run_duration = meter.create_histogram(
    "yoagent.agent.run_duration_ms",
    description="Agent run duration in milliseconds",
)
tool_call_counter = meter.create_counter(
    "yoagent.tool.calls",
    description="Number of tool calls",
)
sandbox_execution_counter = meter.create_counter(
    "yoagent.sandbox.executions",
    description="Number of sandbox executions",
)
sandbox_execution_duration = meter.create_histogram(
    "yoagent.sandbox.duration_ms",
    description="Sandbox execution duration",
)
token_usage_counter = meter.create_counter(
    "yoagent.llm.tokens",
    description="LLM tokens consumed",
)
```

### Step 7: Grafana Dashboard Definitions

**File**: `infra/grafana/dashboards/platform-overview.json`

Key panels:
- Active users, agent count, conversation count
- Error rate (5xx), request latency (p50/p95/p99)
- Agent run success rate
- Token consumption over time

**File**: `infra/grafana/dashboards/agent-performance.json`

Key panels:
- Per-agent success rate, average response time
- Token consumption by agent
- Tool call distribution

**File**: `infra/grafana/dashboards/sandbox-metrics.json`

Key panels:
- Pool utilization, OOM rate
- Execution time distribution
- Active sandboxes gauge

### Step 8: Observability Stack (Docker Compose for dev)

**File**: `infra/docker-compose.observability.yml`

```yaml
services:
  otel-collector:
    image: otel/opentelemetry-collector-contrib:latest
    ports: ["4317:4317", "4318:4318"]
    volumes:
      - ./otel-collector-config.yaml:/etc/otelcol-contrib/config.yaml

  grafana:
    image: grafana/grafana:latest
    ports: ["3001:3000"]
    volumes:
      - ./grafana/dashboards:/var/lib/grafana/dashboards
      - ./grafana/provisioning:/etc/grafana/provisioning

  tempo:
    image: grafana/tempo:latest
    ports: ["3200:3200"]

  loki:
    image: grafana/loki:latest
    ports: ["3100:3100"]

  prometheus:
    image: prom/prometheus:latest
    ports: ["9090:9090"]
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
```

### Step 9: Performance & Availability Targets

| Metric | Target |
|--------|--------|
| Agent first token latency | < 2s (P99) |
| Tool call latency (built-in) | < 500ms |
| Sandbox cold start | < 3s |
| Sandbox warm start | < 500ms |
| API response (non-agent) | < 200ms (P99) |
| Concurrent conversations | 1000+ (single cluster) |
| Platform availability | 99.9% |
| Planned maintenance window | < 4h/month |
| RTO (recovery time) | < 15min |
| RPO (data loss) | < 1min |

### Step 10: Testing Strategy

| Level | Tool | Coverage Target |
|-------|------|-----------------|
| Unit tests | pytest | > 80% line coverage |
| Integration tests | pytest + testcontainers | API → DB → MCP full chain |
| E2E tests | Playwright | Core user flows (create agent → chat → see results) |
| Load tests | Locust | 1000 concurrent conversations |
| Security tests | Trivy + Bandit + OWASP ZAP | CI integration |

### Step 11: Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| LLM provider outage | Multi-provider failover (OpenAI → Anthropic → self-hosted) |
| Sandbox escape | gVisor + seccomp + regular security audits |
| LLM cost runaway | Hard token caps + real-time metering alerts + per-user quotas |
| MCP tool compatibility | Tool health checks + auto-degradation + version locking |
| CopilotKit breaking changes | Wrapper components + version locking + integration tests |
| Cold start latency | Sandbox warm pool + uv package cache + LLM connection pool |
| Cross-tenant data leak | Row-level isolation + automated isolation tests + pen testing |

---

## Integration Points

- **All phases**: OpenTelemetry instruments existing FastAPI, SQLAlchemy, Redis
- **Phase 05**: Sandbox manager upgraded to use gVisor runtime
- **Phase 08**: TLS and secrets management for auth tokens
- **Phase 09**: Usage metrics feed into Grafana dashboards

---

## Verification Checklist

- [ ] `kustomize build infra/k8s/overlays/dev | kubectl apply -f -` — deploys to dev cluster
- [ ] `kustomize build infra/k8s/overlays/prod | kubectl apply -f -` — deploys to prod cluster
- [ ] HPA scales API pods under load
- [ ] gVisor sandbox executes Python code with stronger isolation
- [ ] OpenTelemetry traces visible in Grafana/Tempo
- [ ] Prometheus metrics scraped, dashboards populated
- [ ] Loki log aggregation working
- [ ] Agent first token latency < 2s at P99 under load
- [ ] Sandbox cold start < 3s, warm start < 500ms
- [ ] Load test: 1000 concurrent conversations sustained
- [ ] Security scan (Trivy + Bandit) passes with no critical findings
- [ ] E2E test: create agent → chat → tool call → result — passes

---

## Forward-Looking Notes

- Private deployment guide (Helm chart or Terraform) for enterprise customers.
- Agent-to-Agent communication protocol for complex orchestration.
- Vector store integration (pgvector + RAG) for knowledge-grounded agents.
- Agent template marketplace (community-contributed agent configurations).
- Consider adding canary deployments and blue-green deployment strategies.
