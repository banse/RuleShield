import { h as head } from "../../chunks/index2.js";
/* empty css               */
function _layout($$renderer, $$props) {
  let { children } = $$props;
  head("12qhfyh", $$renderer, ($$renderer2) => {
    $$renderer2.title(($$renderer3) => {
      $$renderer3.push(`<title>RuleShield Dashboard</title>`);
    });
    $$renderer2.push(`<meta name="description" content="RuleShield Hermes - LLM Cost Optimizer Dashboard"/>`);
  });
  $$renderer.push(`<div class="min-h-screen bg-bg">`);
  children($$renderer);
  $$renderer.push(`<!----></div>`);
}
export {
  _layout as default
};
