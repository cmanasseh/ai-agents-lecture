---
name: render-slides
description: Render slides/lecture.md to PNG images to check the layout. Use after editing the slides.
---

Run this. Marp can hang, so the browser timeout and the 60 s alarm are required:

```bash
perl -e 'alarm 60; exec @ARGV' npx -y @marp-team/marp-cli@latest slides/lecture.md \
  --images png --browser-timeout 30 -o /tmp/slides/s.png
```

Then look at every slide you changed in `/tmp/slides/` and report any text that overflows.
