# Handle case when grid cell centroid happens to land on motorway

When blindly routing from grid cell center to nearest urban center, there will be cases
when road distance is larger than expected.

This happens (most likely) due to traveling motorway to "wrong" direction.

## How to detect

If beeline distance is smalle, and road distance is relatively large, one might suspect
that this problem was activated.

## How to mitigate

Cells, where beeline distance and road distances differ (greatly), another computation
round should be activated. New routes should be calculated, e.g. from
* random points
* gridded points, relative to grid coordinates, e.g. (0.25,0.25), (0.25,0.75), (0.75,0.25), (0.75,0.75)

## Implementation estimate

* distance checker limit search (human effort)
* re-looping problematic grid cells
* computing routes
* selecting minimum distance
* detecting if result is valid
* possible refinement with finer new grid