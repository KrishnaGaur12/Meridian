# Frontend Performance Engineering & Optimization

## 1. Bundle & Build Analysis

- **Bundler:** Vite 6 with `@vitejs/plugin-react` and `@tailwindcss/vite`.
- **CSS Strategy:** Tailwind CSS v4 compiles utility classes into a single optimized stylesheet at build time, resulting in minimal CSS payload.
- **Production Artifacts:** Standard ES Modules with content hashing in `dist/assets/`.

---

## 2. Request Optimization & Deduplication

### 2.1 The Request-on-Render & Duplicate Request Problem
In traditional SPAs, multiple child components (e.g., `Header`, `SearchBar`, `DashboardPage`, `DisputeDetailPage`) can trigger duplicate simultaneous HTTP requests for identical resources.

### 2.2 Implemented Solution: Promise Deduplication
In `src/services/cacheService.ts`:
```typescript
const existingPromise = this.inFlightRequests.get(key);
if (existingPromise) {
  return existingPromise as Promise<T>;
}
```
If two components request `GET /disputes` simultaneously, only one network request is dispatched over the wire; both components await the same Promise.

---

## 3. Network Lifecycle & Memory Leak Prevention

### 3.1 AbortController Cancellation
Every page component (`DisputesPage.tsx`, `DisputeDetailPage.tsx`, `HistoryPage.tsx`) instantiates an `AbortController` in `useEffect`:
```typescript
useEffect(() => {
  const controller = new AbortController();
  loadCaseData(false, controller.signal);
  return () => {
    controller.abort();
  };
}, [loadCaseData, modeVersion]);
```
- When the user navigates between pages quickly, any in-flight Axios requests are cancelled instantly.
- Prevents `setState` on unmounted component memory leaks and race conditions.

---

## 4. Why Disputes Screen Performs with Zero Lag

1. **In-Memory Cache (TTL):** Navigating back from Dispute Detail to Disputes Queue serves the cached list instantly (0ms network time).
2. **Optimistic UI Mutations:** Adding or approving evidence updates the DOM in the same JavaScript event loop without waiting for the network round-trip.
3. **Selective Re-rendering:** Components use granular local state to prevent whole-page re-renders during text edits or form interactions.
4. **Debounced Search:** Top search dropdown operates entirely over in-memory dispute lists without spamming the backend server on keystrokes.
