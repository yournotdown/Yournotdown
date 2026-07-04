## Top 3 Safest Next Tasks

1. Review the local diff for `backend/google_places_photos.py`, `backend/server.py`, and `migrations/refresh_google_photo_names.py`, with emphasis on the sanitized Google Places error logging and the dry-run-only refresh flow.
2. In a separate step, provide `DEST_MONGO_URL`, `DEST_DB`, and `GOOGLE_PLACES_API_KEY`, then run `migrations/refresh_google_photo_names.py` in default dry-run mode only to measure how many imported businesses can fetch fresh `photos[].name` values from Places Details New.
3. If the dry-run output looks correct, decide whether to run the same script with `--apply` so it updates only `google_photo_names` and `google_photo_names_refreshed_at`, without touching any other business fields or deleting anything.
