## Top 3 Safest Next Tasks

1. Install frontend dependencies locally, then rerun `npm run build` so the Emergent asset cleanup can be verified with an actual production bundle.
2. After a successful build, open the built frontend in a browser or preview environment and confirm the Network tab no longer requests `https://assets.emergent.sh/scripts/emergent-main.js` and that no `Made with Emergent` badge is rendered.
3. Separately from this frontend cleanup, continue the Google Places photo-name refresh follow-up by reviewing or running the dry-run flow in `migrations/refresh_google_photo_names.py` only when the required local environment variables are available.
