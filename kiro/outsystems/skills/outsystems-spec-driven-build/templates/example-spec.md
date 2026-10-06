# App Spec: TaskTracker

## 1. Overview

**Purpose:** Internal team task tracking — small (M) app where engineers create tasks, assign them to teammates, and track status from Open → InProgress → Done. Replaces our team's ad-hoc Notion board. ~5 engineers will use it daily.

**Target users:** Engineers, Engineering Manager.

**Target app:** TaskTracker (new)

**Style direction:** Apply OutSystems UI defaults — no custom theme needed for v1.

---

## 2. Roles

- **Engineer**: creates and edits their own tasks; views all team tasks; cannot delete tasks; cannot reassign other engineers' tasks.
- **EngineeringManager**: full access — creates, edits, deletes, reassigns any task across the team.

(No anonymous access — this is internal-only.)

---

## 3. Data model

### Entities

| Entity | Attributes | Relationships |
|---|---|---|
| Engineer | Id (Long, mandatory, auto), UserId (User Identifier, optional, unique), Name (Text, 100, mandatory), Email (Email, 256, mandatory, unique), JoinedAt (DateTime, mandatory) | FK to the ODC User who signs in (UserId) |
| Task | Id (Long, mandatory, auto), Title (Text, 200, mandatory), Description (Text, 2000), Status (TaskStatus, mandatory), Priority (TaskPriority, mandatory), CreatedByEngineerId (Long FK → Engineer.Id, mandatory), AssignedToEngineerId (Long FK → Engineer.Id, optional), CreatedAt (DateTime, mandatory), DueDate (Date, optional) | FK to Engineer (twice — creator + assignee) |
| Comment | Id (Long, mandatory, auto), TaskId (Long FK → Task.Id, mandatory), EngineerId (Long FK → Engineer.Id, mandatory), Body (Text, 2000, mandatory), CreatedAt (DateTime, mandatory) | FK to Task + Engineer |

### Static enums

| Enum | Values |
|---|---|
| TaskStatus | Open, InProgress, Blocked, Done, Cancelled |
| TaskPriority | Low, Medium, High, Critical |

---

## 4. Screens + RBAC

| Screen | Purpose | Accessible by |
|---|---|---|
| Login | Auth | Anonymous |
| Dashboard | KPI cards (my open tasks, team's in-progress, this-week-due) + recent activity | All authenticated |
| TaskList | Filter + sort all team tasks | All authenticated |
| TaskDetail | View one task, edit if creator-or-manager, add comments | Engineer (own tasks edit, all view), EngineeringManager (all) |
| TaskCreate | New task form | All authenticated |
| EngineerList | View all team members + their workload | EngineeringManager |
| EngineerDetail | View/edit one engineer (name, email, join date) | EngineeringManager |

---

## 5. Server actions

- **GetMyOpenTasks(EngineerId)** → returns Task list filtered to assignee = EngineerId AND status IN (Open, InProgress). Used by Dashboard.
- **GetTeamWorkloadSummary()** → returns aggregated counts per engineer per status. Used by EngineerList.
- **AssignTask(TaskId, NewAssigneeId, ActingEngineerId)** → updates Task.AssignedToEngineerId, validates ActingEngineer's role allows the operation. Returns success bool.
- **AddComment(TaskId, EngineerId, Body)** → creates a Comment, returns new CommentId.

---

## 6. Integrations

None — fully self-contained for v1.

---

## 7. UI/UX direction

- Theme: OutSystems UI defaults
- Layout style: Dashboard with sidebar nav
- Mobile-responsive: Yes (engineers want to triage tasks from their phone)
- Branding: no constraints

---

## 8. Out of scope

- Public REST endpoints — internal-only for now
- Multi-team isolation — this app is for one team
- Slack / email notifications — nice-to-have, not v1
- File attachments on comments — text-only v1
- Time tracking / hour logging — out of scope

---

## 9. Acceptance criteria

- I can log in as `Engineer` and create a task, assign it to myself, change its status, add a comment.
- I can log in as `EngineeringManager` and reassign someone else's task; an `Engineer` cannot do this.
- Dashboard correctly shows "my open tasks" count for the logged-in engineer.
- At least 10 example tasks seeded across the 5 statuses to make the demo look real.

---

## 10. Notes for Mentor

- Use `Long Integer` for all entity Id columns (not `Integer`, not the `Identifier` shortcut — be explicit).
- Add at least 2 example engineers + 10 example tasks via a `BootstrapData` server action, run by a Timer when the app is published.
- Find the signed-in engineer with `Engineer.UserId = GetUserId()`. When no engineer has that UserId yet, match on `Engineer.Email` and set `UserId`. "My open tasks" and the creator-or-manager edit check use this engineer.
- For TaskList screen, default sort = `CreatedAt DESC` (newest first).
- For the Dashboard, do not include an "all tasks ever" widget — keep it scoped to actionable items.
