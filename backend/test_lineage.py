import unittest

from lineage import (
    LineageValidationError,
    canonical_lineage_manifest,
    lineage_manifest_digest,
    validate_lineage_graph,
)


class LineageManifestTests(unittest.TestCase):
    def test_canonical_lineage_manifest_is_stable(self) -> None:
        manifest = {
            "parentProofIds": ["a" * 64, "b" * 64],
            "operationType": "crop",
            "parametersDigest": "c" * 64,
            "toolIdentity": "harpocrates-studio",
            "toolVersion": "1.2.3",
            "outputDigest": "d" * 64,
            "network": "testnet",
            "actorAddress": "GAJC123",
        }
        first = canonical_lineage_manifest(manifest)
        second = canonical_lineage_manifest(manifest)
        self.assertEqual(first, second)
        self.assertEqual(lineage_manifest_digest(manifest), lineage_manifest_digest(manifest))

    def test_rejects_unsupported_operation(self) -> None:
        with self.assertRaises(LineageValidationError):
            canonical_lineage_manifest({
                "parentProofIds": ["a" * 64],
                "operationType": "unsupported",
                "parametersDigest": "c" * 64,
                "toolIdentity": "harpocrates-studio",
                "toolVersion": "1.2.3",
                "outputDigest": "d" * 64,
                "network": "testnet",
                "actorAddress": "GAJC123",
            })

    def test_rejects_excessive_fanout(self) -> None:
        with self.assertRaises(LineageValidationError):
            canonical_lineage_manifest({
                "parentProofIds": ["a" * 64, "b" * 64, "c" * 64, "d" * 64, "e" * 64],
                "operationType": "compose",
                "parametersDigest": "c" * 64,
                "toolIdentity": "harpocrates-studio",
                "toolVersion": "1.2.3",
                "outputDigest": "d" * 64,
                "network": "testnet",
                "actorAddress": "GAJC123",
            })

    def test_rejects_direct_cycle(self) -> None:
        output = "a" * 64
        with self.assertRaises(LineageValidationError) as ctx:
            validate_lineage_graph(
                parent_proof_ids=[output],
                depth=1,
                actor_address="GAJC123",
                output_digest=output,
            )
        self.assertIn("cycle", str(ctx.exception).lower())

    def test_rejects_missing_actor_address(self) -> None:
        with self.assertRaises(LineageValidationError):
            validate_lineage_graph(
                parent_proof_ids=["a" * 64],
                depth=1,
                actor_address="",
            )

    def test_accepts_valid_lineage_graph(self) -> None:
        # Should not raise
        validate_lineage_graph(
            parent_proof_ids=["a" * 64, "b" * 64],
            depth=1,
            actor_address="GAJC123",
            output_digest="c" * 64,
        )


class LineageListEndpointErrorEnvelopeTests(unittest.TestCase):
    """Tests for the standard error envelope on lineage list endpoints."""

    def setUp(self) -> None:
        try:
            from app import app
        except Exception as exc:  # noqa: BROEART
            self.skipTest(f"app module unavailable: {exc}")
            return
        self.app = app
        self.client = app.test_client()

    def _assert_validation_envelope(self, response) -> None:
        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertIsInstance(payload, dict)
        self.assertIn("error", payload)
        error = payload["error"]
        self.assertIsInstance(error, dict)
        self.assertEqual(error.get("code"), "VALIDATION_ERROR")
        self.assertTruthy(error.get("requestId") or payload.get("requestId"))

    def test_lineage_events_rejects_non_integer_limit(self) -> None:
        response = self.client.get("/api/proofs/lineage?limit=abc")
        self._assert_validation_envelope(response)

    def test_lineage_events_rejects_negative_limit(self) -> None:
        response = self.client.get("/api/proofs/lineage?limit=-1")
        self._assert_validation_envelope(response)

    def test_lineage_by_actor_rejects_non_integer_limit(self) -> None:
        response = self.client.get("/api/proofs/lineage/actor/GAJC123?limit=abc")
        self._assert_validation_envelope(response)

    def test_lineage_by_actor_rejects_negative_limit(self) -> None:
        response = self.client.get("/api/proofs/lineage/actor/GAJC123?limit=-1")
        self._assert_validation_envelope(response)
