/**
 * RuleShield SDK -- Drop-in OpenAI wrapper for Node.js/TypeScript.
 *
 * Usage:
 *   // Before:
 *   import OpenAI from 'openai';
 *   const client = new OpenAI();
 *
 *   // After (one import change):
 *   import { OpenAI } from '@ruleshield/sdk';
 *   const client = new OpenAI();
 *
 *   // Everything else stays the same
 *   const response = await client.chat.completions.create({
 *     model: 'gpt-4o',
 *     messages: [{ role: 'user', content: 'Hello' }],
 *   });
 */

import OriginalOpenAI from 'openai';
import type { ClientOptions } from 'openai';

const RULESHIELD_PROXY_URL = process.env.RULESHIELD_PROXY_URL || 'http://127.0.0.1:8337/v1';

/**
 * Drop-in replacement for the OpenAI client that routes through RuleShield proxy.
 *
 * Automatically sets baseURL to the RuleShield proxy.
 * All other options are passed through to the real OpenAI client.
 *
 * Environment variables:
 *   RULESHIELD_PROXY_URL: Override proxy URL (default: http://127.0.0.1:8337/v1)
 *   OPENAI_API_KEY: Your OpenAI API key (passed through to proxy)
 */
export class OpenAI extends OriginalOpenAI {
  constructor(opts?: ClientOptions) {
    const options: ClientOptions = {
      ...opts,
      baseURL: opts?.baseURL || RULESHIELD_PROXY_URL,
    };
    super(options);
  }
}

/**
 * Configuration helper for RuleShield proxy.
 */
export const RuleShieldConfig = {
  /** Get the current proxy URL */
  getProxyUrl: (): string => RULESHIELD_PROXY_URL,

  /** Check if RuleShield proxy is reachable */
  isAvailable: async (): Promise<boolean> => {
    try {
      const response = await fetch(`${RULESHIELD_PROXY_URL.replace('/v1', '')}/health`);
      return response.ok;
    } catch {
      return false;
    }
  },

  /** Get current savings stats from proxy */
  getStats: async (): Promise<Record<string, unknown> | null> => {
    try {
      const response = await fetch(`${RULESHIELD_PROXY_URL.replace('/v1', '')}/api/stats`);
      if (!response.ok) return null;
      return await response.json() as Record<string, unknown>;
    } catch {
      return null;
    }
  },
};

// Re-export everything from openai for convenience
export * from 'openai';

// Default export for CommonJS compatibility
export default OpenAI;
