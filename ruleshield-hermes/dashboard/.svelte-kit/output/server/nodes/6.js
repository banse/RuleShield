

export const index = 6;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/docs/architecture/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/6.CXnwG4Zi.js","_app/immutable/chunks/DBkhj26I.js","_app/immutable/chunks/D-CXgeZZ.js"];
export const stylesheets = [];
export const fonts = [];
