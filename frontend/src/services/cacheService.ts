/**
 * Fast in-memory cache manager with TTL and key invalidation support.
 * Used to eliminate lag and prevent duplicate API requests.
 */

interface CacheEntry<T> {
  data: T;
  timestamp: number;
  ttlMs: number;
}

class CacheService {
  private cache = new Map<string, CacheEntry<any>>();
  private inFlightRequests = new Map<string, Promise<any>>();

  /**
   * Get cached data if valid, otherwise undefined.
   */
  get<T>(key: string): T | undefined {
    const entry = this.cache.get(key);
    if (!entry) return undefined;

    if (Date.now() - entry.timestamp > entry.ttlMs) {
      this.cache.delete(key);
      return undefined;
    }

    return entry.data as T;
  }

  /**
   * Store data in cache with a TTL (default 30 seconds).
   */
  set<T>(key: string, data: T, ttlMs: number = 30000): void {
    this.cache.set(key, {
      data,
      timestamp: Date.now(),
      ttlMs,
    });
  }

  /**
   * Deduplicate concurrent in-flight requests for the exact same key.
   */
  async dedupe<T>(key: string, fetcher: () => Promise<T>, ttlMs: number = 30000): Promise<T> {
    const cached = this.get<T>(key);
    if (cached !== undefined) {
      return cached;
    }

    const existingPromise = this.inFlightRequests.get(key);
    if (existingPromise) {
      return existingPromise as Promise<T>;
    }

    const promise = fetcher()
      .then((data) => {
        this.set(key, data, ttlMs);
        this.inFlightRequests.delete(key);
        return data;
      })
      .catch((err) => {
        this.inFlightRequests.delete(key);
        throw err;
      });

    this.inFlightRequests.set(key, promise);
    return promise;
  }

  /**
   * Invalidate a single key or all keys matching a prefix.
   */
  invalidate(keyOrPrefix: string): void {
    for (const key of Array.from(this.cache.keys())) {
      if (key === keyOrPrefix || key.startsWith(keyOrPrefix)) {
        this.cache.delete(key);
      }
    }
    for (const key of Array.from(this.inFlightRequests.keys())) {
      if (key === keyOrPrefix || key.startsWith(keyOrPrefix)) {
        this.inFlightRequests.delete(key);
      }
    }
  }

  /**
   * Clear entire cache.
   */
  clear(): void {
    this.cache.clear();
    this.inFlightRequests.clear();
  }
}

export const appCache = new CacheService();
