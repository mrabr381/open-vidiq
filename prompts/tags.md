# Tag generation prompt (Gemini — reference only)

Tags are built locally from the channel's real top keywords (see
`generate.local_tags`): the niche keyword first, then the top keywords
in frequency order, lowercased, at most 15 tags.

If a Gemini rewrite is ever used for tags, it must only re-order or
combine words from that same keyword list — never introduce a new
topic the channel has not covered.
