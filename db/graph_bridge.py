"""
graph_bridge.py
================
Populates the `graph_edges` staging table (see schema_postgis.sql) from
PostGIS data, then exports node/edge CSVs for Neo4j bulk import
(`neo4j-admin database import`) or periodic `LOAD CSV` sync.

Why staging + bulk export instead of dual-writing to Neo4j at ingest
time: buoy/eDNA ingestion runs at sensor frequency and must stay fast
and simple; graph relationship computation (co-occurrence, adjacency,
correlation) is a batch/analytical job that can run on its own schedule
without being on the critical path of ingestion. Every node already
carries a stable UUID from schema_postgis.sql, so there's no id-mapping
step needed when the edges get imported into Neo4j — the UUID *is* the
Neo4j node's business key (stored as a node property, indexed there too).

Requires: pip install asyncpg h3
"""

import asyncio
import csv
import uuid
import h3
import asyncpg

H3_RESOLUTION = 6


async def compute_h3_adjacency_edges(pool: asyncpg.Pool):
    """(:OceanGrid/H3Cell)-[:ADJACENT_TO]->(:OceanGrid/H3Cell) edges,
    derived from H3's k-ring neighbor function — gives GraphRAG queries
    a native "what's near this cell" traversal without recomputing
    spatial distance at query time."""
    async with pool.acquire() as conn:
        cells = await conn.fetch(
            "SELECT DISTINCT h3_index FROM buoy_readings WHERE ts >= now() - INTERVAL '90 days'"
        )
        edges = []
        for row in cells:
            cell = row["h3_index"]
            cell_hex = h3.int_to_str(cell) if hasattr(h3, "int_to_str") else hex(cell)
            neighbors = h3.grid_disk(h3.int_to_str(cell), 1) if hasattr(h3, "grid_disk") else []
            for n in neighbors:
                n_int = h3.str_to_int(n) if hasattr(h3, "str_to_int") else int(n, 16)
                if n_int == cell:
                    continue
                edges.append((str(uuid.uuid4()), str(cell), "H3Cell", str(n_int), "H3Cell",
                               "ADJACENT_TO", "{}", "h3_adjacency_job"))

        await conn.executemany(
            """
            INSERT INTO graph_edges (id, source_id, source_label, target_id, target_label,
                                      relation_type, properties, computed_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
            """,
            edges,
        )
        return len(edges)


async def compute_species_cooccurrence_edges(pool: asyncpg.Pool, min_shared_cells: int = 2):
    """(:Species)-[:CO_OCCURS_WITH]->(:Species) — species whose eDNA
    detections share H3 cells, weighted by number of shared cells.
    This is exactly the kind of multimodal link (molecular biodiversity
    x spatial grid) that's awkward to query repeatedly in SQL but is a
    single Cypher traversal once it's in Neo4j."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT a.species_id AS species_a, b.species_id AS species_b,
                   count(DISTINCT a.h3_index) AS shared_cells
            FROM edna_samples a
            JOIN edna_samples b
              ON a.h3_index = b.h3_index AND a.species_id < b.species_id
            GROUP BY a.species_id, b.species_id
            HAVING count(DISTINCT a.h3_index) >= $1
            """,
            min_shared_cells,
        )
        edges = [
            (str(uuid.uuid4()), str(r["species_a"]), "Species", str(r["species_b"]), "Species",
             "CO_OCCURS_WITH", f'{{"shared_cells": {r["shared_cells"]}}}', "cooccurrence_job")
            for r in rows
        ]
        await conn.executemany(
            """
            INSERT INTO graph_edges (id, source_id, source_label, target_id, target_label,
                                      relation_type, properties, computed_by)
            VALUES ($1, $2, $3, $4, $5, $6, $7::jsonb, $8)
            """,
            edges,
        )
        return len(edges)


async def export_for_neo4j_import(pool: asyncpg.Pool, out_dir: str = "./neo4j_import"):
    """Writes nodes_*.csv and edges.csv in the format expected by
    `neo4j-admin database import full` (headers include :ID, :LABEL,
    :START_ID, :END_ID, :TYPE per Neo4j's CSV header convention)."""
    import os
    os.makedirs(out_dir, exist_ok=True)

    async with pool.acquire() as conn:
        species = await conn.fetch("SELECT id, common_name, scientific_name, family FROM species")
        with open(f"{out_dir}/nodes_species.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id:ID", "common_name", "scientific_name", "family", ":LABEL"])
            for s in species:
                w.writerow([str(s["id"]), s["common_name"], s["scientific_name"], s["family"], "Species"])

        grids = await conn.fetch("SELECT id, grid_code, area_name FROM ocean_grids")
        with open(f"{out_dir}/nodes_grids.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["id:ID", "grid_code", "area_name", ":LABEL"])
            for g in grids:
                w.writerow([str(g["id"]), g["grid_code"], g["area_name"], "OceanGrid"])

        edges = await conn.fetch("SELECT source_id, target_id, relation_type, properties FROM graph_edges")
        with open(f"{out_dir}/edges.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow([":START_ID", ":END_ID", ":TYPE", "properties"])
            for e in edges:
                w.writerow([str(e["source_id"]), str(e["target_id"]), e["relation_type"], str(e["properties"])])

    print(f"Exported {len(species)} species nodes, {len(grids)} grid nodes, {len(edges)} edges to {out_dir}/")
    print("Import with: neo4j-admin database import full --nodes=Species=nodes_species.csv "
          "--nodes=OceanGrid=nodes_grids.csv --relationships=edges.csv bluebyte")


async def _run_all(dsn: str):
    pool = await asyncpg.create_pool(dsn=dsn)
    n1 = await compute_h3_adjacency_edges(pool)
    n2 = await compute_species_cooccurrence_edges(pool)
    print(f"Computed {n1} adjacency edges, {n2} co-occurrence edges")
    await export_for_neo4j_import(pool)
    await pool.close()


if __name__ == "__main__":
    asyncio.run(_run_all("postgresql://user:pass@localhost/bluebyte"))