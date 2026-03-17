

export const index = 5;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/docs/api/_page.svelte.js')).default;
export const imports = ["_app/immutable/nodes/5.y1A7KFZr.js","_app/immutable/chunks/DBkhj26I.js","_app/immutable/chunks/D-CXgeZZ.js"];
export const stylesheets = [];
export const fonts = [];
