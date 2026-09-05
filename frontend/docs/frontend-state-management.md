# Frontend State Management Architecture

## 1. Overview of State Layers

The frontend implements a multi-tier state architecture separating:
1. **Global Environment State** (React Context + LocalStorage)
2. **Server Query State & Cache** (In-Memory `CacheService` with TTL)
3. **Local Component & Optimistic UI State** (React `useState`, `useRef`)
4. **URL & Navigation State** (React Router DOM `useParams`, `useNavigate`)

---

## 2. Global Environment State (`DatabaseModeContext.tsx`)

### 2.1 State Structure
```typescript
export type DatabaseMode = 'DEMO' | 'LIVE';

interface DatabaseModeContextType {
  mode: DatabaseMode;
  isDemo: boolean;
  isLive: boolean;
  setMode: (mode: DatabaseMode) => void;
  toggleMode: () => void;
  isSwitching: boolean;
  modeVersion: number;
}
```

### 2.2 Synchronization Workflow
- When user clicks **"Demo Mode" / "Live Mode"**:
  1. `localStorage.setItem('razorpay_database_mode', newMode)`
  2. `api.defaults.headers.common['X-Database-Mode'] = newMode`
  3. `setModeVersion(v => v + 1)` triggers page-level re-fetches via `useEffect` dependencies.
  4. Top notification banner shows `"Synchronizing workspace with LIVE database..."` during the 300ms transition.

---

## 3. In-Memory Cache & Deduping Engine (`cacheService.ts`)

### 3.1 Key Implementation
```typescript
class CacheService {
  private cache = new Map<string, CacheEntry<any>>();
  private inFlightRequests = new Map<string, Promise<any>>();

  get<T>(key: string): T | undefined { ... }
  set<T>(key: string, data: T, ttlMs: number = 30000): void { ... }
  async dedupe<T>(key: string, fetcher: () => Promise<T>, ttlMs: number = 30000): Promise<T> { ... }
  invalidate(keyOrPrefix: string): void { ... }
  clear(): void { ... }
}
```

### 3.2 Invalidation Strategy
- `submitDispute` invalidates: `disputes_list`, `dispute_${id}`, `command_center_${id}`, `readiness_${id}`, `package_${id}`.
- `createEvidence` / `uploadEvidenceFile` invalidates: `command_center_${id}`, `package_${id}`, `readiness_${id}`, `analysis_${id}`.
- `approveEvidence` invalidates: `command_center_${id}`, `readiness_${id}`, `package_${id}`.

---

## 4. Component-Level Optimistic UI Updates

### 4.1 Implementation in `CaseMerchantControlCenter.tsx`
- When evidence is added or uploaded, a temporary item with a generated ID (`temp_${Date.now()}`) and status `PENDING_APPROVAL` is immediately prepended to `localEvidence`.
- When evidence is approved, `localEvidence` immediately updates the item's status to `APPROVED`, unblocking the submit button instantly while the backend mutation runs asynchronously.
- If backend responds with an error, the local state reverts and an error alert is rendered.
