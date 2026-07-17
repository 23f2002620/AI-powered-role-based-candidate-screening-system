# Frontend Engineering Knowledge Base

## Core Web Platform
The browser rendering pipeline parses HTML into a DOM tree and CSS into a CSSOM, combines them
into a render tree, computes layout (reflow), and paints pixels, followed by compositing layers
on the GPU. Reflow is triggered by geometry changes (width, position) and is more expensive than
repaint (color changes) or compositing-only changes (transform, opacity), which is why CSS
transforms/opacity are preferred for animations. The Critical Rendering Path optimization
involves minimizing render-blocking resources, inlining critical CSS, and deferring
non-essential JavaScript.

## JavaScript Fundamentals
JavaScript is single-threaded with an event loop: the call stack executes synchronous code, the
microtask queue (Promises, queueMicrotask) drains fully before each macrotask (setTimeout,
I/O callbacks, rendering) runs. Closures capture variables from their defining scope, enabling
patterns like memoization and private state. Prototypal inheritance underlies JS's object model;
`class` syntax is sugar over prototype chains. Async/await is sugar over Promises, and unhandled
promise rejections can silently fail without proper try/catch or .catch handling.

## React and Component Architecture
React re-renders components when state or props change, using a virtual DOM diff (reconciliation)
to compute minimal real DOM updates, keyed by the `key` prop for list items to preserve identity
across re-renders. Hooks (useState, useEffect, useMemo, useCallback, useReducer) must follow the
Rules of Hooks (called unconditionally, in the same order every render) because React relies on
call order to associate hook state. useEffect dependency arrays control when effects re-run;
missing dependencies cause stale closures, a common source of subtle bugs. State management
choices range from local component state, to lifting state up, to Context API for cross-cutting
concerns, to external stores (Redux, Zustand, Jotai) for complex or frequently-updated global
state, chosen based on update frequency and how many components need to react to changes.

## Performance
Code splitting (dynamic import(), React.lazy) reduces initial bundle size by loading routes or
components on demand. Memoization (React.memo, useMemo, useCallback) avoids unnecessary
re-renders and recomputation but has its own comparison overhead, so it should be applied where
profiling shows a real cost, not by default everywhere. Core Web Vitals (LCP - Largest
Contentful Paint, FID/INP - responsiveness, CLS - Cumulative Layout Shift) are the standard
metrics for perceived performance; image optimization (responsive images via srcset, modern
formats like WebP/AVIF, lazy loading offscreen images) commonly has the largest impact on LCP.

## State Management and Data Fetching
Client-server state synchronization is a distinct problem from local UI state; libraries like
React Query/TanStack Query or SWR handle caching, background refetching, stale-while-revalidate
semantics, and request deduplication for server data, which is different from state that only
exists on the client. Optimistic updates improve perceived responsiveness by updating the UI
before server confirmation, with rollback logic on failure.

## Accessibility and Semantics
Semantic HTML elements (nav, button, header, main) provide built-in accessibility semantics that
ARIA attributes should supplement, not replace, per the "no ARIA is better than bad ARIA"
principle. Keyboard navigability (focus order, visible focus states, skip links) and screen
reader support (labeled form controls, live regions for dynamic content) are essential for WCAG
compliance. Color contrast ratios (4.5:1 for normal text under WCAG AA) ensure readability.

## Styling and Design Systems
CSS specificity is calculated from ID, class/attribute/pseudo-class, and element selectors;
cascade layers and the :is()/:where() pseudo-classes give finer control over specificity
conflicts. Utility-first CSS (Tailwind) trades some HTML verbosity for colocation of styling and
markup and smaller final bundle sizes via purging unused classes. CSS-in-JS solutions add
runtime or build-time cost but colocate styles with component logic. Design tokens (spacing
scales, color palettes, typography scales) create consistency across a design system and make
theming/dark-mode support tractable.

## Testing and Tooling
Testing pyramids for frontend typically favor many unit tests (component logic, pure functions),
fewer integration tests (component interactions, React Testing Library encouraging testing
behavior over implementation details), and a small number of end-to-end tests (Cypress,
Playwright) that are slower and more brittle but catch real user-flow regressions. Bundlers
(Vite, Webpack) perform tree-shaking to eliminate unused exports, code splitting, and
transform modern syntax for target browser compatibility via tools like Babel or esbuild.
