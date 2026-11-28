"""Lot peaufinage B (2026-11-25) — identité du club (v2-cadrage §3.4, option A).

- PUT /api/club/theme : couleurs hexadécimales (1ʳᵉ obligatoire, 2ᵉ et 3ᵉ
  optionnelles) + logo PNG ou SVG statique ≤ 500 Ko, validé côté serveur
  (type par les octets, taille, pas de dynamique dans le SVG) ;
- l'identité est commune au club (clé = nom du club normalisé) et servie par
  GET /api/moi (« theme », null si le club n'en a pas) ;
- logo null ou absent = suppression ; repli : aucun thème → « theme: null ».

Isolement identique à test_auth_app.py (RTRL_APP_DB → base temporaire).
"""
import base64
import unittest

import app_store

from test_auth_app import AuthAppTestBase, call_json, token_of

PNG_MINIMAL = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
SVG_MINIMAL = (
    "<svg xmlns='http://www.w3.org/2000/svg'><rect width='8' height='8'/></svg>"
).encode("utf-8")


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


class ThemeClubTests(AuthAppTestBase):
    def _inscrire_club(self, login="coach.a", club="FC Rive"):
        code, body, setc = call_json(
            "/api/auth/inscription", "POST",
            data={
                "login": login,
                "password": "azerty1234",
                "club": club,
                "categorie": "U8",
            },
        )
        self.assertEqual(code, 201, body)
        return token_of(setc)

    def _put(self, token, corps):
        return call_json("/api/club/theme", "PUT", data=corps, cookie=token)


class LectureThemeTests(ThemeClubTests):
    """Repli : /api/moi renvoie « theme: null » tant que le club n'en a pas."""

    def test_moi_theme_null_par_defaut(self):
        token = self._inscrire_club()
        code, moi, _ = call_json("/api/moi", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(moi["club"], "FC Rive")
        self.assertIsNone(moi["theme"])

    def test_moi_sans_club_theme_toujours_null(self):
        token = self._inscrire()  # compte sans club
        code, moi, _ = call_json("/api/moi", cookie=token)
        self.assertEqual(code, 200)
        self.assertIsNone(moi["club"])
        self.assertIsNone(moi["theme"])


class EcritionThemeTests(ThemeClubTests):
    """PUT /api/club/theme : cas limites et enregistrement."""

    def test_put_sans_session_401(self):
        code, body, _ = self._put(
            None, {"couleurs": {"primary": "#0b5d3b"}, "logo": None}
        )
        self.assertEqual(code, 401)
        self.assertIn("error", body)

    def test_put_sans_club_400(self):
        token = self._inscrire()  # compte sans club
        code, body, _ = self._put(
            token, {"couleurs": {"primary": "#0b5d3b"}, "logo": None}
        )
        self.assertEqual(code, 400)
        self.assertIn("sans club", body["error"])

    def test_put_couleurs_absentes_400(self):
        token = self._inscrire_club()
        code, body, _ = self._put(token, {"couleurs": {}, "logo": None})
        self.assertEqual(code, 400)
        self.assertIn("principale", body["error"])

    def test_put_primary_non_hexadecimale_400(self):
        token = self._inscrire_club()
        for primary in ("rouge", "#fff", "0b5d3b", "#0B5D3BGG", ""):
            code, body, _ = self._put(
                token, {"couleurs": {"primary": primary}, "logo": None}
            )
            self.assertEqual(code, 400, f"primary={primary!r}")
            self.assertIn("hexadécimale", body["error"])

    def test_put_couleur_secondaire_invalide_400(self):
        token = self._inscrire_club()
        code, body, _ = self._put(
            token,
            {"couleurs": {"primary": "#0b5d3b", "secondary": "zzz"}, "logo": None},
        )
        self.assertEqual(code, 400)
        self.assertIn("secondaire", body["error"])

    def test_put_corps_non_objet_400(self):
        token = self._inscrire_club()
        code, body, _ = self._put(token, [1, 2])
        self.assertEqual(code, 400)
        self.assertIn("error", body)

    def test_put_valide_renvoie_theme(self):
        token = self._inscrire_club()
        code, res, _ = self._put(
            token,
            {
                "couleurs": {"primary": "#0b5d3b", "secondary": "#d9e8e1"},
                "logo": None,
            },
        )
        self.assertEqual(code, 200, res)
        self.assertEqual(
            res["theme"]["couleurs"],
            {"primary": "#0b5d3b", "secondary": "#d9e8e1", "accent": None},
        )
        self.assertIsNone(res["theme"]["logo"])
        # Le thème est ensuite servi par /api/moi.
        code, moi, _ = call_json("/api/moi", cookie=token)
        self.assertEqual(code, 200)
        self.assertEqual(moi["theme"], res["theme"])

    def test_put_couleurs_optionnelles_vides_enregistrees_null(self):
        token = self._inscrire_club()
        code, res, _ = self._put(
            token,
            {
                "couleurs": {
                    "primary": "#101216",
                    "secondary": "",
                    "accent": "",
                },
                "logo": None,
            },
        )
        self.assertEqual(code, 200, res)
        self.assertIsNone(res["theme"]["couleurs"]["secondary"])
        self.assertIsNone(res["theme"]["couleurs"]["accent"])

    def test_put_upsert_remplace_l_identite(self):
        token = self._inscrire_club()
        self._put(token, {"couleurs": {"primary": "#0b5d3b"}, "logo": None})
        code, res, _ = self._put(
            token, {"couleurs": {"primary": "#a01020"}, "logo": None}
        )
        self.assertEqual(code, 200)
        self.assertEqual(res["theme"]["couleurs"]["primary"], "#a01020")
        self.assertIsNone(res["theme"]["couleurs"]["secondary"])


class LogoTests(ThemeClubTests):
    """Logo : validation côté serveur (octets, taille, SVG statique)."""

    def test_put_logo_png_valide(self):
        token = self._inscrire_club()
        code, res, _ = self._put(
            token, {"couleurs": {"primary": "#0b5d3b"}, "logo": b64(PNG_MINIMAL)}
        )
        self.assertEqual(code, 200, res)
        logo = res["theme"]["logo"]
        self.assertTrue(logo.startswith("data:image/png;base64,"), logo)
        # La data URI est la lecture directe de ce qui a été envoyé.
        self.assertEqual(
            base64.b64decode(logo.partition(",")[2]), PNG_MINIMAL
        )

    def test_put_logo_svg_valide(self):
        token = self._inscrire_club()
        code, res, _ = self._put(
            token, {"couleurs": {"primary": "#0b5d3b"}, "logo": b64(SVG_MINIMAL)}
        )
        self.assertEqual(code, 200, res)
        self.assertTrue(res["theme"]["logo"].startswith("data:image/svg+xml;base64,"))

    def test_put_logo_base64_illisible_400(self):
        token = self._inscrire_club()
        code, body, _ = self._put(
            token, {"couleurs": {"primary": "#0b5d3b"}, "logo": "!!! pas du b64"}
        )
        self.assertEqual(code, 400)
        self.assertIn("base64", body["error"])

    def test_put_logo_octets_inconnus_refuses(self):
        token = self._inscrire_club()
        # Ni la signature PNG, ni du texte UTF-8 commençant par <svg.
        code, body, _ = self._put(
            token, {"couleurs": {"primary": "#0b5d3b"}, "logo": b64(b"PK\x03\x04xyz")}
        )
        self.assertEqual(code, 400)
        self.assertIn("Logo refusé", body["error"])

    def test_put_logo_svg_dynamique_refuse(self):
        token = self._inscrire_club()
        pour_svg = (
            b"<svg xmlns='http://www.w3.org/2000/svg' onload=alert(1)>",
            b"<svg><script>alert(1)</script></svg>",
            b"<svg><a href='javascript:alert(1)'></a></svg>",
        )
        for svg in pour_svg:
            code, body, _ = self._put(
                token, {"couleurs": {"primary": "#0b5d3b"}, "logo": b64(svg)}
            )
            self.assertEqual(code, 400, f"svg={svg!r}")
            self.assertIn("Logo refusé", body["error"])

    def test_put_logo_trop_lourd_refuse(self):
        token = self._inscrire_club()
        trop_grand = b"\x89PNG\r\n\x1a\n" + b"x" * app_store.LOGO_MAX_OCTETS
        code, body, _ = self._put(
            token, {"couleurs": {"primary": "#0b5d3b"}, "logo": b64(trop_grand)}
        )
        self.assertEqual(code, 400)
        self.assertIn("500 Ko", body["error"])

    def test_put_logo_null_supprime_l_existant(self):
        token = self._inscrire_club()
        self._put(token, {"couleurs": {"primary": "#0b5d3b"}, "logo": b64(PNG_MINIMAL)})
        code, res, _ = self._put(
            token, {"couleurs": {"primary": "#0b5d3b"}, "logo": None}
        )
        self.assertEqual(code, 200)
        self.assertIsNone(res["theme"]["logo"])

    def test_put_remplace_le_logo_existants(self):
        token = self._inscrire_club()
        self._put(token, {"couleurs": {"primary": "#0b5d3b"}, "logo": b64(PNG_MINIMAL)})
        code, res, _ = self._put(
            token, {"couleurs": {"primary": "#0b5d3b"}, "logo": b64(SVG_MINIMAL)}
        )
        self.assertEqual(code, 200)
        self.assertTrue(res["theme"]["logo"].startswith("data:image/svg+xml;base64,"))


class PorteeClubTests(ThemeClubTests):
    """L'identité est commune au club (clé = nom du club), pas au compte."""

    def test_theme_partage_entre_les_comptes_du_club(self):
        token_a = self._inscrire_club("coach.a", "FC Rive")
        token_b = self._inscrire_club("coach.b", "FC Rive")
        self._put(token_a, {"couleurs": {"primary": "#0b5d3b"}, "logo": b64(SVG_MINIMAL)})
        code, moi_b, _ = call_json("/api/moi", cookie=token_b)
        self.assertEqual(code, 200)
        self.assertEqual(moi_b["theme"]["couleurs"]["primary"], "#0b5d3b")
        self.assertIsNotNone(moi_b["theme"]["logo"])

    def test_autre_club_voit_son_theme_null(self):
        self._inscrire_club("coach.a", "FC Rive")
        token_autre = self._inscrire_club("coach.c", "FC Bord")
        self._put(
            self._inscrire_club("coach.d", "FC Rive"),
            {"couleurs": {"primary": "#0b5d3b"}, "logo": None},
        )
        code, moi, _ = call_json("/api/moi", cookie=token_autre)
        self.assertEqual(code, 200)
        self.assertIsNone(moi["theme"])

    def test_clubs_nom_normalise_meme_identite(self):
        # « FC Rive » et «  FC Rive  » désignent le même club (strip, comme
        # l'enregistrement) : une seule identité, pas deux.
        token_a = self._inscrire_club("coach.a", " FC Rive")
        token_b = self._inscrire_club("coach.b", "FC Rive ")
        self._put(token_a, {"couleurs": {"primary": "#0b5d3b"}, "logo": None})
        code, moi_b, _ = call_json("/api/moi", cookie=token_b)
        self.assertEqual(code, 200)
        self.assertEqual(moi_b["theme"]["couleurs"]["primary"], "#0b5d3b")


class MethodeTests(ThemeClubTests):
    def test_get_non_autorise_405(self):
        # Un GET ne doit pas tomber dans le fallback statique (200 index.html)
        # : la route renvoie un 405 explicite.
        code, body, _ = call_json("/api/club/theme")
        self.assertEqual(code, 405)
        self.assertIn("error", body)


if __name__ == "__main__":
    unittest.main()
