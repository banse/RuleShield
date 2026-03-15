# Dashboard: Add dark/light mode toggle

**Labels:** `good first issue`, `help wanted`, `dashboard`, `enhancement`, `UI`

## Description

The RuleShield dashboard currently has a dark theme only (hardcoded in CSS variables). Add a toggle button in the header that switches between dark and light mode, persisting the user's preference in `localStorage`.

## Why this is useful

Not everyone prefers dark mode, especially when viewing dashboards in well-lit environments or presenting cost savings data to stakeholders. A light mode option improves accessibility and makes the dashboard usable in more contexts. This is also a great way to learn the dashboard's theming system, which uses CSS custom properties exclusively.

## Where to look in the codebase

### Theme definition

**File:** `dashboard/src/app.css`

All colors are defined as CSS custom properties inside the `@theme` block:

```css
@theme {
  --color-bg: #0A0A0F;
  --color-surface: #12121A;
  --color-surface-elevated: #1A1A26;
  --color-border: #2A2A3C;
  --color-primary: #6C5CE7;
  --color-accent: #00D4AA;
  --color-text-primary: #F0F0F5;
  --color-text-secondary: #A0A0B8;
  --color-text-muted: #6B6B82;
  /* ... */
}
```

### Layout (where to add the toggle)

**File:** `dashboard/src/routes/+layout.svelte`

This is the root layout component. Currently very simple -- just wraps children in a `min-h-screen bg-bg` div. The toggle could be added here, or in the header section of `+page.svelte`.

### Dashboard header

**File:** `dashboard/src/routes/+page.svelte`

The header section (line ~86) has a flex layout with the RuleShield logo on the left and connection status on the right. The theme toggle should go between them or next to the connection status indicator.

### Tech stack

- **Framework:** SvelteKit 5 (uses `$state` runes, `$derived`, `$props`)
- **Styling:** Tailwind CSS 4 with `@theme` directive
- **No component library** -- all UI is hand-built with Tailwind classes

## Implementation approach

### 1. Define light theme colors

Add a light theme variant in `dashboard/src/app.css`. You can use a `[data-theme="light"]` selector or a `.light` class on the root element:

```css
[data-theme="light"] {
  --color-bg: #F8F9FC;
  --color-surface: #FFFFFF;
  --color-surface-elevated: #F0F1F5;
  --color-border: #E2E4EA;
  --color-text-primary: #1A1A2E;
  --color-text-secondary: #4A4A6A;
  --color-text-muted: #8A8AA0;
  /* Keep primary/accent colors the same for brand consistency */
}
```

### 2. Add toggle logic

Create the toggle state in the layout or page component. Use `localStorage` to persist the choice:

```svelte
<script>
  import { onMount } from 'svelte';
  let theme = $state('dark');

  onMount(() => {
    theme = localStorage.getItem('ruleshield-theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
  });

  function toggleTheme() {
    theme = theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ruleshield-theme', theme);
  }
</script>
```

### 3. Add toggle button to the header

Place a sun/moon icon toggle in the header bar next to the connection status.

## Acceptance criteria

- [ ] A toggle button (or icon) is visible in the dashboard header
- [ ] Clicking the toggle switches between a dark and light theme
- [ ] The theme preference persists across page reloads (stored in `localStorage` under a key like `ruleshield-theme`)
- [ ] All text remains readable in both modes (sufficient contrast)
- [ ] The primary (`#6C5CE7`) and accent (`#00D4AA`) brand colors remain consistent in both themes
- [ ] The toggle has a visual indicator showing which mode is active (e.g., sun icon for light, moon icon for dark)
- [ ] No flash of wrong theme on page load (apply stored theme before first paint, or use a `<script>` in `app.html`)
- [ ] All existing dashboard sections (metric cards, savings panel, request table, rules table, shadow mode panel) look correct in both themes

## Estimated difficulty

**Medium** -- Requires understanding CSS custom properties, SvelteKit lifecycle (`onMount`), and localStorage. The main challenge is choosing good light theme colors that keep the dashboard looking professional.

## Helpful links and references

- [Dashboard CSS](../../dashboard/src/app.css) -- Current theme variables
- [Dashboard layout](../../dashboard/src/routes/+layout.svelte) -- Root layout component
- [Dashboard page](../../dashboard/src/routes/+page.svelte) -- Main dashboard UI
- SvelteKit `onMount`: https://svelte.dev/docs/svelte/lifecycle-hooks
- Tailwind CSS theming: https://tailwindcss.com/docs/dark-mode
