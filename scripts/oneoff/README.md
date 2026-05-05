# scripts/oneoff/

Archive folder for one-shot scripts that have already been run on every
environment that needed them.

## Workflow

1. Author the script in `src/app/migrations/` so it ships inside the backend
   image and is runnable via `docker exec`.
2. Run it on every environment that needs it (prod, staging, etc).
3. Move the file from `src/app/migrations/` to `scripts/oneoff/`. The next
   image build no longer carries it, so the container does not bloat with
   dead code.
4. When nobody will ever rerun it, `git rm` it. Git history keeps the source.

The point of this folder is to avoid the failure mode where one-shots pile
up indefinitely inside the image, while still keeping a brief
"ran-this-on-prod" trail in the repo before final deletion.
