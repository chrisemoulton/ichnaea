=========
Changelog
=========

1.4 (unreleased)
================

Untagged
********

Migrations
~~~~~~~~~~

- 40d609897296: Add sharded cell tables.

Changes
~~~~~~~

- Use sharded cell tables.

- Keep separate rate limits per API version.

- Update to latest versions of dependencies.

20151118134500
**************

Migrations
~~~~~~~~~~

- 91fb41d12c5: Drop mapstat table.

Changes
~~~~~~~

- #469: Update to static tabzilla.

- #468: Add CORS headers and support OPTIONS requests.

- #467: Implement geodude compatibility API.

- Choose best WiFi cluster based on a data quality score.

- Use up to top 10 WiFi networks in WiFi location.

- Use proper agglomerative clustering in WiFi clustering.

- Remove arithmetic/hamming distance analysis of BSSIDs.

- Accept and forward WiFi SSID's in public HTTP API's.

20151105120300
**************

Migrations
~~~~~~~~~~

- 78e6322b4d9: Copy mapstat data to sharded datamap tables.

- 4e8635b0f4cf: Add sharded datamap tables.

Changes
~~~~~~~

- Use new sharded datamap tables.

- Parallelize datamap CSV export, Quadtree generation and upload.

- Introduce upper bound for cell based accuracy numbers.

- Fix database lookup fallback in API key check.

- Switch randomness generator for data map, highlight more recent additions.

- Update to latest versions of lots of dependencies.

20151021143400
**************

Migrations
~~~~~~~~~~

- 450f02b5e1ca: Update cell_area regions.

- 582ef9419c6a: Add region stat table.

- 238aca86fe8d: Change cell_area primary key.

- 3fd11bfaca02: Drop api_key log column.

- 583a68296584: Drop old OCID cell/area tables.

- 2c709f81a660: Rename cell/area columns to radius/samples.

Changes
~~~~~~~

- Maintain `block_first` column.

- Introduce upper bound for Wifi based accuracy numbers.

- Provide better GeoIP accuracy numbers for cities and subdivisions.

- Fix cell queries containing invalid area codes but valid cids.

- #242: Add WiFi stats to region specific stats page.

- Add update_statregion task to maintain region_stat table.

- Update to latest versions of alembic, coverage, datadog, raven
  and requests.

20151013115000
**************

Migrations
~~~~~~~~~~

- 33d0f7fb4da0: Add api_type specific logging flags to api keys.

- 460ce3d4fe09: Rename columns to region.

- 339d19da63ee: Add new cell OCID tables.

- All OCID data has to be manually imported again into the new tables.

Changes
~~~~~~~

- Add new `fallback_allowed` tag to locate metrics.

- Calculate region radii based on precise shapefiles.

- Use subunits dataset to preserve smaller regions.

- Use GENC codes and names in GeoIP results.

- Consider more responses as high accuracy.

- Change internal names to refer to region.

- Change metric tag to region for region codes.

- Temporarily stop using cell/area range in locate logic.

- Discard too large cell networks during import.

- Use mcc in region determination for cells.

- Use new OCID tables in the entire code base.

- Use the intersection of region codes from GENC and our shapefile.

- Avoid base64/json overhead for simple queues containing byte values.

- Maintain a queue TTL value and process remaining data for inactive queues.

- Remove hashkey functionality from cell area models.

- Remove non-sharded update_wifi queue.

- Merge scan_areas/update_area tasks into a single new update_cellarea task.

- Remove backwards compatible tasks and area/mapstat task processing logic.

- Update to latest versions of bower, clean-css and uglify-js.

- Update to latest versions of cryptography, Cython, kombu, numpy,
  pyasn1, PyMySQL, requests, Shapely, six and WebOb.

20150928100200
**************

Migrations
~~~~~~~~~~

- 26c4b3a7bc51: Add new datamap table.

- 47ed7a40413b: Add cell area id columns.

Changes
~~~~~~~

- Improve locate accuracy by taking station circle radius into account.

- Split out OCID cell area updates to their own queue.

- Switch mapstat queue to compact binary queue values.

- Speed up update_area task by only loading required cell columns.

- Validate all incoming reports against the region areas.

- Add a precision reverse geocoder for region lookups.

- Add a finer grained region border file in GeoJSON format.

- Shard update_wifi queue/task by the underlying table shard id.

- Update datatables JS library and fix default column ordering.

- Switch to GENC dataset for region names.

- #372: Add geocoding / search control to map.

- Support the new `considerIp` field in the geolocate API.

- #389: Treat accuracy, altitude and altitudeAccuracy as floats.

- Speed up `/stats/regions` by using cell area table.

- Use cell area ids in update_cellarea task queue.

- Enable country level result metrics.

- Removed migrations before version 1.2.

- Update to latest versions of numpy, pytz, raven, rtree and Shapely.
