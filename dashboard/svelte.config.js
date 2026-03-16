import adapterAuto from '@sveltejs/adapter-auto';
import adapterStatic from '@sveltejs/adapter-static';

const exportSlides = process.env.RULESHIELD_EXPORT_SLIDES === '1';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: exportSlides
			? adapterStatic({
					pages: 'build/slides-static',
					assets: 'build/slides-static',
					strict: false
				})
			: adapterAuto(),
		prerender: exportSlides
			? {
					entries: ['/slides'],
					crawl: false,
					handleHttpError: 'warn'
				}
			: undefined
	},
	vitePlugin: {
		dynamicCompileOptions: ({ filename }) =>
			filename.includes('node_modules') ? undefined : { runes: true }
	}
};

export default config;
