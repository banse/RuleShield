

export const index = 13;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/slides/_page.svelte.js')).default;
export const universal = {
  "ssr": false
};
export const universal_id = "src/routes/slides/+page.ts";
export const imports = ["_app/immutable/nodes/13.BFSY7_lC.js","_app/immutable/chunks/DBkhj26I.js","_app/immutable/chunks/D-CXgeZZ.js","_app/immutable/chunks/5DWYZtkS.js","_app/immutable/chunks/Dcyew59p.js","_app/immutable/chunks/AXXK6pST.js","_app/immutable/chunks/Bsyb4nzI.js","_app/immutable/chunks/CUQdtjJL.js","_app/immutable/chunks/BTiu4Uyx.js","_app/immutable/chunks/B4x7B47p.js"];
export const stylesheets = ["_app/immutable/assets/13.C03tTEeX.css"];
export const fonts = [];
