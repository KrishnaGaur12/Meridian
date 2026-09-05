# Frontend UI & Component Reference Guide

## 1. Common UI Components (`src/components/common/`)

### 1.1 Badge (`Badge.tsx`)
- **Props:** `variant?: 'neutral' | 'urgent' | 'important' | 'success' | 'info' | 'outline'`, `children`, `className`.
- **Purpose:** Renders status and priority labels with standardized Tailwind colors.

### 1.2 Button (`Button.tsx`)
- **Props:** `variant?: 'primary' | 'secondary' | 'outline' | 'danger' | 'ghost'`, `size?: 'sm' | 'md' | 'lg'`, `isLoading?: boolean`, `disabled?`.
- **Purpose:** Accessible button with integrated SVG spinning indicator for async loading states.

### 1.3 Modal (`Modal.tsx`)
- **Props:** `isOpen: boolean`, `onClose: () => void`, `title: string`, `subtitle?: string`, `maxWidth?: 'sm' | 'md' | 'lg' | 'xl'`, `children`, `footer`.
- **Behavior:** Backdrop blur, `Escape` key dismiss listener, body scroll lock, accessible focus container.

### 1.4 SearchBar (`SearchBar.tsx`)
- **Behavior:** Fetches disputes on mount, filters by query string across ID, Customer, and Reason, displays instant dropdown, dismisses on outside click.

### 1.5 Skeleton (`Skeleton.tsx`)
- **Purpose:** Animated pulsing placeholder (`animate-pulse bg-slate-200/80`) to represent async data loading.

---

## 2. Dispute Domain Components (`src/components/disputes/`)

### 2.1 CaseMerchantControlCenter (`CaseMerchantControlCenter.tsx`)
The primary 85KB dispute operations component:
- **Backend Lifecycle Stepper:** 11-step progress bar from dispute intake to final outcome.
- **AI Verdict & Win Probability Card:** Win likelihood (0–100%), fraud score, confidence badge, positive/negative winning factor bullets, and DeepSeek explanation.
- **Evidence Management Workspace:**
  - *Add Evidence Modal:* Upload tab (PDF/PNG/JPG) + Manual tab (Carrier tracking).
  - *Edit Metadata Modal:* Edit title, description, and type.
  - *Replace File Modal:* Replace backing file without losing record ID.
  - *Delete Confirmation Modal:* Remove stale records.
  - *Inspect Facts Modal:* View extracted facts and validation details.
  - *Approve Action:* Single-click merchant sign-off.
- **Defense Rebuttal Editor:** Custom defense statement editor to persist merchant response.
- **Submission Readiness Gate:** Lists blocking issues; unblocks the final submission button once criteria are satisfied.

### 2.2 CaseOverviewTab (`CaseOverviewTab.tsx`)
- High-level case summary containing 12 critical parameters, risk preview, attention banner, and chronological audit trail.

### 2.3 CaseRazorpayReviewTab (`CaseRazorpayReviewTab.tsx`)
- Displays gateway reference ID, submission timestamp, contested amount, and gateway outcome simulator button.

### 2.4 CaseOutcomeTab (`CaseOutcomeTab.tsx`)
- Displays final resolution (WON / LOST / CONCEDED), financial impact (+₹ / -₹), and complete chronological database audit history.

### 2.5 WorkflowStepNav (`WorkflowStepNav.tsx`)
- 4-step merchant journey navigation tabs:
  1. *Overview*
  2. *Review & Control Center*
  3. *Gateway Review*
  4. *Final Outcome*
