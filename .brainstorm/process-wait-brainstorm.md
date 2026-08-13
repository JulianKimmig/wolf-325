# Process-wait improvement candidates

- Add a checked catalogue-generation command that regenerates
  `src/wolf_325/register_catalogue.json` from the reference register map and
  fails when committed metadata drifts. This would make future register-map
  updates reproducible instead of relying on a one-off extraction command.
