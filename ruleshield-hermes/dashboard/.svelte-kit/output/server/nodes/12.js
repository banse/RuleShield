import * as server from '../entries/pages/rules/_page.server.ts.js';

export const index = 12;
let component_cache;
export const component = async () => component_cache ??= (await import('../entries/pages/rules/_page.svelte.js')).default;
export { server };
export const server_id = "src/routes/rules/+page.server.ts";
export const imports = ["_app/immutable/nodes/12.BMWd-Ddf.js","_app/immutable/chunks/DBkhj26I.js","_app/immutable/chunks/D-CXgeZZ.js","_app/immutable/chunks/CqvsL0Zu.js","_app/immutable/chunks/5DWYZtkS.js","_app/immutable/chunks/Dcyew59p.js","_app/immutable/chunks/AXXK6pST.js","_app/immutable/chunks/Bsyb4nzI.js","_app/immutable/chunks/BTiu4Uyx.js","_app/immutable/chunks/B4x7B47p.js","_app/immutable/chunks/kWXGTQMu.js"];
export const stylesheets = [];
export const fonts = [];
