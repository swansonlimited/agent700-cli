# Enterprise Runtime RFC

**Status:** Draft  
**Author:** AI Assistant  
**Last Updated:** 2026-04-17  
**Spec Path:** /docs/specs/2026-04-17-enterprise-runtime-rfc.md

---

## Problem & Motivation

`agent700-cli` is currently a useful terminal client for interacting with Agent700 agents, but it is still much closer to a single-user CLI than a true enterprise runtime.

The target product is stricter and more ambitious:

- runs on employee machines through a CLI and TUI
- supports business messaging surfaces, starting with **Microsoft Teams** and **Google Chat**
- works with multiple model providers through API keys or OAuth
- can generate files and work products, not just chat replies
- supports durable agent work, scheduled work, and auditability
- supports **multi-user organizations** with governed visibility across user memory and work

This RFC defines the architectural direction for evolving `agent700-cli` into a local-first, enterprise-applicable agent runtime.

---

## Product Positioning

### What we want to borrow

From **Hermes Agent**:
- durable memory and cross-session continuity
- provider flexibility
- persistent work patterns

From **OpenClaw**:
- strong orchestration boundaries
- explicit sessions and scheduling
- approval and security posture

From **Paperclip**:
- enterprise governance mindset
- tenant-aware orchestration
- auditability, durable work, and operational oversight

### What should set `agent700-cli` apart

`agent700-cli` should not try to become a consumer assistant or an agent-company simulator.

It should become:
- an **enterprise CLI/TUI agent runtime**
- deployable to client businesses
- usable on employee workstations
- easy to connect to enterprise SaaS, internal APIs, and MCP tools
- good at generating durable work products, files, reports, and artifacts
- auditable and reproducible at the org, user, run, and tool-action level

---

## Goals

- Add a first-class **enterprise runtime model**: orgs, users, agents, runs, memories, schedules, policies.
- Preserve a **local-first edge runtime** on employee machines.
- Add a **governed control-plane contract** for enterprise oversight.
- Support **Microsoft Teams**, **Google Chat**, and **TUI** as the initial operator surfaces.
- Support provider-agnostic model access via API key and OAuth-based auth flows.
- Make artifact generation a first-class outcome, not an afterthought.
- Ensure all sensitive actions and memory access can be audited.

---

## Non-Goals

- Becoming a general-purpose multi-agent company simulator.
- Rebuilding the entire product around a web UI before the runtime model is sound.
- Giving org admins invisible, unlogged access to user-private memory.
- Mixing consumer chat assumptions into enterprise channel integrations.
- Solving autonomous learning loops in this phase.

---

## Core Design Principles

1. **Edge first, control plane second**
   - tool execution and local artifact work happen on the employee machine
   - org policy, audit, and governed visibility live in a control plane

2. **Every action has an actor**
   - user, agent, org admin, scheduled job, and system actions must be attributable

3. **Memory is scoped, not global**
   - memory must have ownership, visibility, provenance, and policy

4. **Runs are durable and replayable**
   - if the enterprise cannot reconstruct what happened, the system is not done

5. **Channels are adapters, not the core product**
   - Teams and Google Chat should map into the same runtime model as TUI, not fork behavior

6. **Artifacts are first-class outputs**
   - generated files, reports, notes, and documents should be represented in the run ledger

---

## Proposed Runtime Model

### 1. Edge Runtime

Runs on the employee machine.

Responsibilities:
- TUI and local CLI interaction
- local shell/tool execution
- local file access and artifact generation
- local session persistence
- local caches and encrypted secrets
- local private memory store
- channel connector workers when installed locally

### 2. Org Control Plane

Can be local-to-org or hosted by the client business.

Responsibilities:
- org and user identity
- policy distribution
- schedule definitions
- org-shared memory
- audit/event ingestion
- admin oversight
- run and artifact index
- compliance exports
- secure relay registration for connected edge runtimes

### 3. Relay / Gateway Layer

Enterprise chat channels like Microsoft Teams and Google Chat require stable webhook targets and app endpoints. A laptop-local CLI cannot satisfy that requirement by itself.

Responsibilities:
- receive inbound webhooks and app events from Teams and Google Chat
- authenticate and normalize external tenant and user identities
- route events to the correct org and connected edge runtime
- buffer or fail safely when an edge runtime is offline
- broker artifact uploads or attachment delivery when work products originate on the local machine

This relay may be part of the control plane, but it is a distinct architectural concern and should be modeled explicitly.

### 4. Shared Contract Between Them

The edge runtime should sync structured records, not ad hoc blobs:
- run envelopes
- audit events
- memory metadata and eligible content
- artifact manifests
- policy versions
- schedule assignments
- relay connection status and channel routing bindings

---

## Top-Level Entities

### Organization
A tenant boundary for a client business.

### User
An employee or contractor operating inside an organization.

### Agent
A configured assistant identity bound to a user, team, or org role.

### Workspace
A local or remote work context containing files, tools, policies, and memory bindings.

### Run
A durable unit of work with inputs, tool actions, outputs, artifacts, and outcome.

### Memory Item
A recorded preference, note, summary, fact, or provenance-linked knowledge object.

### Artifact
A generated or referenced file output, such as a report, spreadsheet, markdown note, or exported document.

### Schedule
A durable automation definition with actor identity, target scope, policy, and execution history.

### Policy
A versioned ruleset governing tool access, memory visibility, approvals, channels, and retention.

### Audit Event
An immutable event describing a material action in the system.

---

## Memory Model

The current llm-wiki work is a good local substrate, but it is not yet the enterprise memory system.

### Required memory scopes

- `user_private`
- `user_shared_to_org`
- `org_shared`
- `system_reference`

### Every memory item should include

- memory id
- org id
- owner user id or owning scope
- visibility scope
- source type
- provenance links
- created/updated timestamps
- policy tags
- retention / deletion metadata
- optional artifact links

### Hard rule

Enterprise visibility into user memory must be:
- explicit in policy
- audit-logged
- queryable by scope
- reviewable later

No silent supervisor memory scraping.

---

## Run Ledger and Reproducibility

A serious enterprise product needs a durable run ledger.

Each run should capture:
- run id
- org id
- user id
- agent id
- channel or surface
- model provider and model id
- policy version
- prompt/input envelope
- tool calls and results
- approvals requested and granted
- artifacts created or modified
- memory reads and writes
- timestamps and final outcome

The goal is not just debugging. The goal is:
- reproducibility
- auditability
- supportability
- compliance review

---

## Artifact Model

`agent700-cli` should be good at generating files, not just chat replies.

Artifacts should be first-class records with:
- artifact id
- producing run id
- path or URI
- content type
- checksum
- source inputs
- creator actor
- visibility and sharing policy
- export/download metadata

Examples:
- markdown notes
- meeting summaries
- spreadsheets
- csv outputs
- reports
- generated code or patches
- internal handoff documents

---

## Channel Strategy

### Initial channels

- **TUI**
- **Microsoft Teams**
- **Google Chat**

These are the right initial business surfaces because most target organizations already live in Microsoft 365 or Google Workspace.

### Channel architecture rule

Treat channels as **adapters into the same runtime**, not separate products. But for Teams and Google Chat, that adapter cannot live only on the employee laptop.

Each inbound channel event should normalize into:
- actor
- org
- user mapping
- channel context
- policy context
- session or run target
- relay routing target

### Relay requirement

For v1 business channels, assume a **central relay/gateway** is mandatory.

Why:
- Teams and Google Chat need stable webhook endpoints
- employee laptops sleep, disconnect, change networks, and should not be public web servers
- enterprise attachment delivery often requires server-mediated upload or channel API calls

The product should therefore model business messaging as:
1. channel event hits central relay
2. relay authenticates tenant and user context
3. relay routes to the correct edge runtime or durable queue
4. edge runtime performs local work and returns outputs or artifacts
5. relay delivers the response or attachment back to the channel

### Microsoft Teams strategy notes

Use Microsoft 365 app and bot patterns with explicit tenant admin installation and consent.

Key needs:
- tenant-aware installation model
- user mapping to org identities
- explicit permissions for chat, channel, and file surfaces
- audit-aware handling of message actions and attachments
- clear separation between personal chat, team channel, and system-triggered runs

### Google Chat strategy notes

Use Google Workspace app patterns with explicit workspace admin installation.

Key needs:
- workspace-scoped installation and consent
- user mapping to workspace identities
- thread-aware interaction model
- predictable event normalization for messages, mentions, and cards
- careful treatment of file and Drive-linked content provenance

### Channel non-goals for v1

- broad consumer messaging support
- many low-value chat surfaces at once
- bespoke channel behavior that bypasses policy and audit layers

---

## Provider and MCP Strategy

### Model provider layer

Introduce a provider abstraction that supports:
- API key auth
- OAuth flows when appropriate
- provider/model capabilities
- model routing and fallback
- usage metering
- org policy constraints on allowed providers

### MCP and enterprise integrations

The product should make API and MCP integration easy, but safely so.

Required boundaries:
- org-approved MCP registry
- per-agent allowlists
- per-run tool tracing
- secrets scoped by org/user/agent
- capability discovery without implicit execution

---

## Orchestration and Persistent Work

The runtime needs durable work, not just conversation history.

Required concepts:
- durable jobs
- resumable runs
- child runs or delegated runs
- waiting states
- retries
- policy-aware approvals
- wake and schedule triggers

This is where OpenClaw and Paperclip are the best references:
- OpenClaw for session and scheduling boundaries
- Paperclip for governance and durable work accounting

---

## Security Model

Security is not a late-phase hardening item. It is a foundation for tenancy, memory scope, orchestration, and channels.

### Minimum requirements

- versioned policy model
- RBAC for org admins, managers, and users
- explicit tool allow/deny rules
- approval gates for sensitive actions
- sandbox modes for risky execution
- secret scoping and redaction
- audit logging for memory access and tool execution
- channel-to-identity mapping controls
- relay authentication and edge-runtime registration rules

### Dangerous mistakes to avoid

- one global memory namespace
- one global session store across users
- unscoped secrets
- unlogged admin access to memory
- scheduled jobs with no clear actor identity
- channel adapters that bypass policy enforcement
- treating local logs as sufficient for enterprise auditability
- assuming cron on employee laptops is reliable without central awareness

---

## Recommended Branch Sequence

1. `docs/enterprise-runtime-rfc`
   - define entities, boundaries, control-plane split, non-goals, and phased roadmap

2. `feature/provider-abstraction-v1`
   - establish the core LLM/provider contract, auth methods, capabilities, and usage accounting

3. `feature/security-policy-rbac-v1`
   - establish policy, approvals, RBAC, secret scopes, and execution boundaries before deeper runtime work

4. `feature/org-user-agent-tenancy`
   - first-class org, user, agent, and local state roots

5. `feature/control-plane-sync-v1`
   - policy sync, edge-runtime registration, relay bindings, and centralized control-plane contracts

6. `feature/run-audit-telemetry-v1`
   - durable run ledger, centralized audit events, artifact manifests, and replay-ready telemetry

7. `feature/memory-scopes-v1`
   - scoped memory objects and visibility rules across user and org boundaries

8. `feature/orchestration-jobs-v1`
   - durable jobs, resumable work, delegation model, waiting states

9. `feature/relay-channel-gateway-v1`
   - central relay/gateway for Teams and Google Chat routing, attachment brokering, and offline-safe delivery

10. `feature/cron-scheduler-v1`
   - scheduled execution with actor identity and audit history, built on top of secure jobs and centralized awareness

11. `feature/ms-teams-adapter-v1`
   - tenant-aware Teams integration on top of the relay model

12. `feature/google-chat-adapter-v1`
   - workspace-aware Google Chat integration on top of the relay model

13. `feature/org-admin-observability-v1`
   - admin visibility, audit search, memory access review, exports

### Why this order

Security cannot come eighth. Business channels cannot come before a relay model exists. Centralized audit and control-plane sync need to exist before the system claims enterprise reproducibility or governed oversight.

---

## Proposed Milestones

### Milestone 1: Foundation and trust boundaries
- provider abstraction
- security policy and RBAC
- tenancy
- control-plane sync

### Milestone 2: Audit and memory backbone
- run/audit telemetry
- memory scopes
- artifact manifests and replay posture

### Milestone 3: Durable work
- orchestration jobs
- cron scheduling with central awareness
- TUI polish against the same runtime model

### Milestone 4: business channels
- relay/gateway
- Teams adapter
- Google Chat adapter

### Milestone 5: admin oversight
- org observability
- memory audit access
- exports and compliance views

---

## RFC Outline for Follow-on Specs

Each follow-on branch spec should cover:

1. problem and motivation
2. goals and non-goals
3. actor model
4. entity model
5. state transitions
6. policy implications
7. audit implications
8. migration strategy
9. open questions
10. rollout and verification

---

## Open Questions

- What portion of the control plane already exists inside Agent700 versus needing new contracts?
- Should the run ledger be fully local-first with sync, or centrally assigned and mirrored locally?
- What memory content is allowed to sync to the org by default?
- Are Teams and Google Chat adapters local, centrally hosted, or mixed?
- What approval and retention requirements do target client businesses already expect?

---

## Immediate Next Step

After the llm-wiki PR, the next correct move is **not** another feature branch.

It is to agree on this runtime model and then start with:
- provider abstraction
- security and RBAC
- tenancy plus control-plane sync

Those three define the safe shape of everything else.
