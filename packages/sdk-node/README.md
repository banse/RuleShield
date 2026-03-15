# @ruleshield/sdk

Drop-in OpenAI SDK wrapper that routes through [RuleShield](https://github.com/banse/ruleshield-hermes) proxy for automatic LLM cost optimization.

## Installation

```bash
npm install @ruleshield/sdk openai
```

## Usage

```typescript
// Before:
import OpenAI from 'openai';

// After (one line change):
import { OpenAI } from '@ruleshield/sdk';

// Everything else stays exactly the same
const client = new OpenAI();

const response = await client.chat.completions.create({
  model: 'gpt-4o',
  messages: [{ role: 'user', content: 'Hello' }],
});
```

## Configuration

Set the proxy URL via environment variable:

```bash
export RULESHIELD_PROXY_URL=http://localhost:8337/v1
```

## Utilities

```typescript
import { RuleShieldConfig } from '@ruleshield/sdk';

// Check if proxy is running
const available = await RuleShieldConfig.isAvailable();

// Get savings stats
const stats = await RuleShieldConfig.getStats();
console.log(`Saved: ${stats?.savings_pct}%`);
```

## Requirements

- Node.js 18+
- RuleShield proxy running (`ruleshield start`)
- OpenAI SDK (`openai` package)

## License

MIT
