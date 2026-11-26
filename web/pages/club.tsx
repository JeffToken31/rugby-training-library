// Lot L4 (2026-11-25) — page « Club » : les coachs du club (comptes +
// coachs sans compte) et les équipes par catégorie, joueurs en prénom + nom
// seul (RGPD v1.1). Statique, sans SSR — même gabarit que /connexion.
// « Préparer une séance » écrit un snapshot en localStorage puis bascule
// sur le constructeur : aucun écran intermédiaire (lib/prefill.ts).
// Lot peaufinage C (2026-11-25) : par équipe, deux zones distinctes —
// « Effectif » (créer/modifier les joueurs) et « Groupes » (groupes nommés
// librement, composés des joueurs déjà créés dans l'effectif ; un joueur au
// plus dans un groupe, règle imposée par le serveur).
// Lot P4 (2026-11-26, charter-workflows critère 4) : vue « ma catégorie »
// — un compte portant une catégorie ouvre la page filtrée sur sa catégorie
// (équipes), avec bascule « voir tout le club » ; un compte sans catégorie
// garde la vue club entière. Le magasin joueurs du club (lot P3) est lu en
// lecture seule : le gestionnaire saisit, les coachs lisent (D4).

import { useEffect, useState } from "react";
import {
  ajouterCoach,
  fetchMoi,
  listerCoachs,
  listerEquipes,
  listerJoueurs,
  mettreAJourEquipe,
  mettreAJourThemeClub,
  supprimerCoach,
  type CoachRef,
  type Moi,
} from "../lib/auth";
import type { Equipe, GroupeEquipe } from "../lib/types";
import { equipesVisibles } from "../lib/club-view";
import { ecrirePrefill } from "../lib/prefill";
import { appliquerThemeClub } from "../lib/theme";

// Miroir de la liste contrôlée du lot club (app_store.py CATEGORIES).
const CATEGORIES = ["babys", "U6", "U8", "U10", "U12", "U14", "U16", "U18", "Autre"];

// Lot peaufinage B : format hexadécimal attendu (miroir de COULEUR_RE,
// app_store.py) — la 1re couleur est obligatoire, les 2 autres effaçables.
const HEX_RE = /^#[0-9a-fA-F]{6}$/;

function CouleurSlot({
  id,
  label,
  valeur,
  onChange,
}: {
  id: string;
  label: string;
  valeur: string;
  onChange: (v: string) => void;
}) {
  const hexOk = HEX_RE.test(valeur);
  // Le sélecteur exige toujours un hex valide : valeur vierge/illisible →
  // noir affiché, le champ texte reste la source de vérité.
  const pick = hexOk ? valeur : "#000000";
  return (
    <div className="club-couleur">
      <label className="club-couleur-label" htmlFor={`hex-${id}`}>
        {label}
      </label>
      <input
        type="color"
        className="club-couleur-pick"
        value={pick}
        aria-label={`${label} — sélecteur`}
        onChange={(e) => onChange(e.target.value)}
      />
      <input
        id={`hex-${id}`}
        type="text"
        className="club-couleur-hex"
        value={valeur}
        placeholder="#0b5d3b"
        maxLength={7}
        autoCapitalize="none"
        spellCheck={false}
        onChange={(e) => onChange(e.target.value)}
      />
      {!hexOk && valeur !== "" && (
        <span className="club-couleur-err" role="alert">
          Format hexadécimal #RRGGBB attendu.
        </span>
      )}
    </div>
  );
}

function EquipeCard({
  eq,
  majEquipe,
  preparer,
}: {
  eq: Equipe;
  majEquipe: (patch: {
    joueurs?: string[];
    groupes?: GroupeEquipe[];
  }) => Promise<void>;
  preparer: () => void;
}) {
  const [nomJoueur, setNomJoueur] = useState("");
  const [nomGroupe, setNomGroupe] = useState("");
  const [enCours, setEnCours] = useState(false);
  const [erreur, setErreur] = useState<string | null>(null);

  const ajouterJoueur = async () => {
    if (enCours) return;
    const nom = nomJoueur.trim().replace(/\s+/g, " ");
    if (nom.length < 2 || nom.length > 80) {
      setErreur("Nom du joueur : 2 à 80 caractères.");
      return;
    }
    setEnCours(true);
    setErreur(null);
    try {
      await majEquipe({ joueurs: [...eq.joueurs, nom] });
      setNomJoueur("");
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Ajout du joueur impossible.");
    } finally {
      setEnCours(false);
    }
  };

  // Le serveur impose l'inclusion (joueur d'un groupe ∈ effectif) : retirer
  // un joueur de l'effectif l'en retire donc aussi de tous ses groupes.
  const retirerJoueur = async (j: string) => {
    if (enCours) return;
    setEnCours(true);
    setErreur(null);
    try {
      await majEquipe({
        joueurs: eq.joueurs.filter((x) => x !== j),
        groupes: eq.groupes.map((g) =>
          g.joueurs.includes(j)
            ? { ...g, joueurs: g.joueurs.filter((x) => x !== j) }
            : g
        ),
      });
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Retrait du joueur impossible.");
    } finally {
      setEnCours(false);
    }
  };

  const creerGroupe = async () => {
    if (enCours) return;
    const nom = nomGroupe.trim().replace(/\s+/g, " ");
    if (nom.length < 2 || nom.length > 80) {
      setErreur("Nom du groupe : 2 à 80 caractères.");
      return;
    }
    setEnCours(true);
    setErreur(null);
    try {
      await majEquipe({ groupes: [...eq.groupes, { nom, joueurs: [] }] });
      setNomGroupe("");
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Création du groupe impossible.");
    } finally {
      setEnCours(false);
    }
  };

  const retirerGroupe = async (index: number) => {
    if (enCours) return;
    if (!window.confirm(`Retirer le groupe « ${eq.groupes[index].nom} » ?`)) return;
    setEnCours(true);
    setErreur(null);
    try {
      await majEquipe({ groupes: eq.groupes.filter((_, i) => i !== index) });
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Retrait du groupe impossible.");
    } finally {
      setEnCours(false);
    }
  };

  const ajouterJoueurAGroupe = async (index: number, joueur: string) => {
    if (enCours) return;
    setEnCours(true);
    setErreur(null);
    try {
      await majEquipe({
        groupes: eq.groupes.map((g, i) =>
          i === index ? { ...g, joueurs: [...g.joueurs, joueur] } : g
        ),
      });
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Ajout au groupe impossible.");
    } finally {
      setEnCours(false);
    }
  };

  const retirerJoueurDuGroupe = async (index: number, joueur: string) => {
    if (enCours) return;
    setEnCours(true);
    setErreur(null);
    try {
      await majEquipe({
        groupes: eq.groupes.map((g, i) =>
          i === index
            ? { ...g, joueurs: g.joueurs.filter((x) => x !== joueur) }
            : g
        ),
      });
    } catch (e) {
      setErreur(e instanceof Error ? e.message : "Retrait du groupe impossible.");
    } finally {
      setEnCours(false);
    }
  };

  // « Joueurs disponibles » : dans l'effectif, pas encore dans un groupe
  // (un joueur au plus dans un groupe — règle serveur).
  const dansUnGroupe = new Set(eq.groupes.flatMap((g) => g.joueurs));
  const disponibles = eq.joueurs.filter((j) => !dansUnGroupe.has(j));

  return (
    <div className="club-team">
      <div className="club-team-head">
        <span className="club-team-name">{eq.nom}</span>
        <span className="club-effectif">
          {eq.joueurs.length > 0
            ? `${eq.joueurs.length} joueur${eq.joueurs.length > 1 ? "s" : ""}`
            : eq.effectif !== null
              ? `effectif déclaré : ${eq.effectif}`
              : "effectif non précisé"}
        </span>
      </div>

      <div className="club-team-zones">
        <section className="club-zone" aria-labelledby={`effectif-${eq.id}`}>
          <h3 className="club-zone-title" id={`effectif-${eq.id}`}>
            Effectif
          </h3>

          {eq.joueurs.length > 0 && (
            <div className="club-players">
              {eq.joueurs.map((j) => (
                <span key={j} className="player-chip">
                  {j}
                  <button
                    type="button"
                    className="chip-x"
                    aria-label={`Retirer ${j}`}
                    disabled={enCours}
                    onClick={() => void retirerJoueur(j)}
                  >
                    ×
                  </button>
                </span>
              ))}
            </div>
          )}

          <div className="club-player-add">
            <input
              type="text"
              placeholder="Prénom et nom d'un joueur"
              value={nomJoueur}
              maxLength={80}
              onChange={(e) => setNomJoueur(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void ajouterJoueur();
                }
              }}
            />
            <button type="button" disabled={enCours} onClick={() => void ajouterJoueur()}>
              Ajouter
            </button>
          </div>
        </section>

        <section className="club-zone" aria-labelledby={`groupes-${eq.id}`}>
          <h3 className="club-zone-title" id={`groupes-${eq.id}`}>
            Groupes
          </h3>

          {eq.groupes.length === 0 && (
            <p className="club-note">
              Aucun groupe : créez-en avec un nom libre, puis placez-y les
              joueurs de l'effectif (un joueur au plus dans un groupe).
            </p>
          )}

          {eq.groupes.map((g, i) => (
            <div key={`${g.nom}-${i}`} className="club-group-card">
              <div className="club-group-head">
                <span className="club-group-name">{g.nom}</span>
                <button
                  type="button"
                  className="chip-x"
                  aria-label={`Retirer le groupe ${g.nom}`}
                  disabled={enCours}
                  onClick={() => void retirerGroupe(i)}
                >
                  ×
                </button>
              </div>
              {g.joueurs.length > 0 && (
                <div className="club-group-joueurs">
                  {g.joueurs.map((j) => (
                    <span key={j} className="player-chip">
                      {j}
                      <button
                        type="button"
                        className="chip-x"
                        aria-label={`Retirer ${j} du groupe ${g.nom}`}
                        disabled={enCours}
                        onClick={() => void retirerJoueurDuGroupe(i, j)}
                      >
                        ×
                      </button>
                    </span>
                  ))}
                </div>
              )}
              {disponibles.length > 0 && (
                <div className="club-group-ajout">
                  {disponibles.map((j) => (
                    <button
                      key={j}
                      type="button"
                      className="club-group-add-chip"
                      disabled={enCours}
                      onClick={() => void ajouterJoueurAGroupe(i, j)}
                    >
                      + {j}
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}

          <div className="club-group-add">
            <input
              type="text"
              placeholder="Nom d'un groupe (ex. « bleus »)"
              value={nomGroupe}
              maxLength={80}
              onChange={(e) => setNomGroupe(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void creerGroupe();
                }
              }}
            />
            <button type="button" disabled={enCours} onClick={() => void creerGroupe()}>
              Créer
            </button>
          </div>
        </section>
      </div>

      {erreur && (
        <p className="club-err" role="alert">
          {erreur}
        </p>
      )}

      <button type="button" className="club-prep" onClick={preparer}>
        Préparer une séance
      </button>
    </div>
  );
}

export default function Club() {
  const [moi, setMoi] = useState<Moi | null>(null);
  const [verifie, setVerifie] = useState(false);
  const [coachs, setCoachs] = useState<CoachRef[]>([]);
  const [coachsErr, setCoachsErr] = useState<string | null>(null);
  const [equipes, setEquipes] = useState<Equipe[]>([]);
  const [equipesErr, setEquipesErr] = useState<string | null>(null);
  // Lot P4 — magasin joueurs du club (lecture seule) et bascule « tout »
  // de la vue « ma catégorie » (fausse par défaut : un compte portant une
  // catégorie ouvre la page filtrée sur sa catégorie).
  const [joueurs, setJoueurs] = useState<string[]>([]);
  const [joueursErr, setJoueursErr] = useState<string | null>(null);
  const [vueTout, setVueTout] = useState(false);
  const [nomCoach, setNomCoach] = useState("");
  const [coachEnCours, setCoachEnCours] = useState(false);
  const [coachMsg, setCoachMsg] = useState<string | null>(null);

  // Lot peaufinage B — identité du club. `couleurs` = textes bruts (source
  // de vérité) ; le logo est soit un fichier choisi (`logoFile` + URL objet
  // en `logoPreview`), soit le logo actuel du club (base64 + data URI depuis
  // /api/moi), soit retiré (les deux nuls).
  const [couleurs, setCouleurs] = useState({ primary: "", secondary: "", accent: "" });
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [logoPreview, setLogoPreview] = useState<string | null>(null);
  const [logoB64, setLogoB64] = useState<string | null>(null);
  const [logoUri, setLogoUri] = useState<string | null>(null);
  const [logoNom, setLogoNom] = useState("");
  const [themeMsg, setThemeMsg] = useState<string | null>(null);
  const [themeEnCours, setThemeEnCours] = useState(false);

  // Thème persisté côté client (même gabarit que les autres pages).
  useEffect(() => {
    const saved = window.localStorage.getItem("rtrl-theme");
    if (saved === "dark" || saved === "light") {
      document.documentElement.dataset.theme = saved;
    }
  }, []);

  // État explicite : on ne liste coachs/équipes que si la session est active.
  useEffect(() => {
    void fetchMoi()
      .then(setMoi)
      .catch(() => setMoi(null))
      .finally(() => setVerifie(true));
  }, []);

  // Lot peaufinage B : l'identité du club s'applique à la surface entière
  // (lib/theme.ts), dérivée du thème clair/sombre courant ; le formulaire
  // est prérempli depuis /api/moi (rechargé après chaque enregistrement).
  useEffect(() => {
    if (!moi) return;
    appliquerThemeClub(moi.theme ?? null);
    if (moi.theme) {
      setCouleurs({
        primary: moi.theme.couleurs.primary,
        secondary: moi.theme.couleurs.secondary ?? "",
        accent: moi.theme.couleurs.accent ?? "",
      });
      setLogoUri(moi.theme.logo);
      if (moi.theme.logo) {
        const fin = moi.theme.logo.indexOf(";base64,");
        setLogoB64(fin >= 0 ? moi.theme.logo.slice(fin + 8) : null);
        setLogoNom("logo actuel");
      } else {
        setLogoB64(null);
        setLogoNom("");
      }
    }
  }, [moi]);

  useEffect(() => {
    if (!moi) return;
    void listerCoachs()
      .then(setCoachs)
      .catch((e: Error) => setCoachsErr(e.message));
    void listerEquipes()
      .then(setEquipes)
      .catch((e: Error) => setEquipesErr(e.message));
    void listerJoueurs()
      .then(setJoueurs)
      .catch((e: Error) => setJoueursErr(e.message));
  }, [moi]);

  const rafraichirCoachs = () =>
    void listerCoachs()
      .then(setCoachs)
      .catch((e: Error) => setCoachsErr(e.message));

  const ajouterCoachNom = async () => {
    if (coachEnCours || !moi) return;
    const nom = nomCoach.trim().replace(/\s+/g, " ");
    if (nom.length < 2 || nom.length > 80) {
      setCoachMsg("Nom du coach : 2 à 80 caractères.");
      return;
    }
    setCoachEnCours(true);
    setCoachMsg(null);
    try {
      await ajouterCoach(nom, moi.club || null);
      setNomCoach("");
      rafraichirCoachs();
    } catch (e) {
      setCoachMsg(e instanceof Error ? e.message : "Ajout du coach impossible.");
    } finally {
      setCoachEnCours(false);
    }
  };

  const retirerCoach = async (c: CoachRef) => {
    if (c.id === null) return;
    if (!window.confirm(`Retirer ${c.nom} de vos coachs ?`)) return;
    setCoachMsg(null);
    try {
      await supprimerCoach(c.id);
      setCoachs((liste) => liste.filter((x) => x.nom !== c.nom || x.login !== null));
    } catch (e) {
      setCoachMsg(e instanceof Error ? e.message : "Suppression du coach impossible.");
    }
  };

  // --- Lot peaufinage B : identité du club ------------------------------

  const choisirLogo = (fichier: File | null) => {
    if (!fichier) return;
    if (fichier.size > 500 * 1000) {
      setThemeMsg(
        "Logo trop lourd : 500 Ko maximum (le format est vérifié à l'enregistrement)."
      );
      return;
    }
    setLogoFile(fichier);
    setLogoPreview(URL.createObjectURL(fichier));
    setLogoNom(fichier.name);
    setThemeMsg(null);
  };

  const retirerLogo = () => {
    if (!window.confirm("Retirer le logo du club ?")) return;
    setLogoFile(null);
    setLogoPreview(null);
    setLogoB64(null);
    setLogoUri(null);
    setLogoNom("");
  };

  const lireBase64 = (fichier: File) =>
    new Promise<string>((resoudre, rejeter) => {
      const lecteur = new FileReader();
      lecteur.onload = () => {
        const uri = lecteur.result as string;
        const fin = uri.indexOf(";base64,");
        resoudre(fin >= 0 ? uri.slice(fin + 8) : "");
      };
      lecteur.onerror = () => rejeter(lecteur.error);
      lecteur.readAsDataURL(fichier);
    });

  const enregistrerIdentite = async () => {
    if (themeEnCours || !moi) return;
    const primary = couleurs.primary.trim();
    if (!HEX_RE.test(primary)) {
      setThemeMsg("Couleur 1 (principale) : format hexadécimal #RRGGBB attendu.");
      return;
    }
    const douce = couleurs.secondary.trim();
    if (douce !== "" && !HEX_RE.test(douce)) {
      setThemeMsg("Couleur 2 (douce) : format hexadécimal #RRGGBB attendu.");
      return;
    }
    const accent = couleurs.accent.trim();
    if (accent !== "" && !HEX_RE.test(accent)) {
      setThemeMsg("Couleur 3 (accent) : format hexadécimal #RRGGBB attendu.");
      return;
    }
    setThemeEnCours(true);
    setThemeMsg(null);
    try {
      const logo = logoFile ? await lireBase64(logoFile) : logoB64;
      await mettreAJourThemeClub({
        couleurs: { primary, secondary: douce || null, accent: accent || null },
        logo,
      });
      const rafraichi = await fetchMoi();
      if (rafraichi) setMoi(rafraichi); // re-préremplit et ré-applique le thème
      setThemeMsg("Identité du club enregistrée.");
    } catch (e) {
      setThemeMsg(e instanceof Error ? e.message : "Enregistrement impossible.");
    } finally {
      setThemeEnCours(false);
    }
  };

  // Mise à jour complète (PUT = corps entier, lot peaufinage C) : on renvoie
  // le corps complet avec les champs modifiés (joueurs et/ou groupes) ; l'équipe
  // est rétablie depuis la réponse du serveur (normalisation, inclusion
  // effectif, unicité « un joueur dans un groupe » — faits là-bas).
  const majEquipe =
    (id: string) =>
    (patch: { joueurs?: string[]; groupes?: GroupeEquipe[] }) =>
      mettreAJourEquipe(
        id,
        (() => {
          const eq = equipes.find((x) => x.id === id);
          if (!eq) throw new Error("Équipe introuvable.");
          return {
            nom: eq.nom,
            club: eq.club,
            categorie: eq.categorie,
            effectif: eq.effectif,
            coachs: eq.coachs,
            joueurs: patch.joueurs ?? eq.joueurs,
            groupes: patch.groupes ?? eq.groupes,
          };
        })()
      ).then((maj) => setEquipes((liste) => liste.map((x) => (x.id === maj.id ? maj : x))));

  const preparer = (eq: Equipe) => {
    ecrirePrefill({
      team: {
        id: eq.id,
        nom: eq.nom,
        club: eq.club,
        categorie: eq.categorie,
        effectif: eq.effectif,
      },
      joueurs: eq.joueurs,
      groupes: eq.groupes,
      coach_par_defaut: eq.coachs[0] ?? moi?.login ?? null,
    });
    // Navigation complète : la page principale consomme le snapshot à
    // l'ouverture (lib/prefill.ts, consommation unique).
    window.location.href = "/";
  };

  // Équipes groupées par catégorie (ordre CATEGORIES, « Sans catégorie » à la
  // fin). Le badge de catégorie vient de la section, pas de l'équipe.
  // Lot P4 — vue « ma catégorie » : si le compte porte une catégorie et que
  // la bascule « tout » n'est pas activée, les équipes sont restreintes à
  // cette catégorie (lib/club-view.ts) ; sinon, vue club entière.
  const equipesFiltrees = equipesVisibles(
    equipes,
    moi?.categorie ?? null,
    vueTout
  );
  const sections = CATEGORIES.map((cat) => ({
    cat,
    equipes: equipesFiltrees.filter((e) => e.categorie === cat),
  }))
    .filter((s) => s.equipes.length > 0)
    .concat([
      {
        cat: "Sans catégorie",
        equipes: equipesFiltrees.filter((e) => !e.categorie),
      },
    ]);

  return (
    <div className="app">
      <header className="app-header">
        <div className="app-title-row">
          <a className="back-btn" href="/" aria-label="Retour au catalogue">
            ←
          </a>
          <h1 className="app-title">Club</h1>
        </div>
      </header>

      <main className="app-main">
        {verifie && !moi ? (
          <div className="connexion-card">
            <p>
              Connectez-vous pour voir les coachs et les équipes de votre club.
            </p>
            <a className="connexion-submit" href="/connexion">
              Se connecter
            </a>
          </div>
        ) : verifie && moi ? (
          <>
            <section className="club-header-card">
              {moi.theme?.logo && (
                <img className="club-logo" src={moi.theme.logo} alt="Logo du club" />
              )}
              <span className="club-header-name">
                {moi.club || "Votre club"}
              </span>
              {moi.categorie && (
                <>
                  <span className="club-badge">{moi.categorie}</span>
                  <button
                    type="button"
                    className="club-tout"
                    aria-pressed={vueTout}
                    onClick={() => setVueTout((v) => !v)}
                  >
                    {vueTout ? "Voir ma catégorie" : "Voir tout le club"}
                  </button>
                </>
              )}
            </section>

            <section className="club-section" aria-labelledby="titre-identite">
              <h2 id="titre-identite" className="club-section-title">
                Identité du club
              </h2>
              <p className="club-note">
                Logo et couleurs du club, affichés sur toute l'application par
                tous les comptes du club. Logo en PNG ou SVG statique,
                500 Ko maximum.
              </p>

              <div className="club-logo-row">
                {(logoPreview || logoUri) && (
                  <img
                    className="club-logo-preview"
                    src={logoPreview ?? logoUri!}
                    alt="Aperçu du logo du club"
                  />
                )}
                <button
                  type="button"
                  className="club-file-btn"
                  onClick={() => document.getElementById("logo-fichier")?.click()}
                >
                  Choisir un logo
                </button>
                <input
                  id="logo-fichier"
                  type="file"
                  accept="image/png,image/svg+xml"
                  style={{ display: "none" }}
                  aria-hidden="true"
                  onChange={(e) => choisirLogo(e.target.files?.[0] ?? null)}
                />
                {logoNom && <span className="club-logo-fichier">{logoNom}</span>}
                {(logoFile || logoB64) && (
                  <button type="button" className="club-logo-remove" onClick={retirerLogo}>
                    Retirer
                  </button>
                )}
              </div>

              <CouleurSlot
                id="p1"
                label="Couleur 1 (principale) — boutons, focus"
                valeur={couleurs.primary}
                onChange={(v) => setCouleurs((c) => ({ ...c, primary: v }))}
              />
              <CouleurSlot
                id="p2"
                label="Couleur 2 (douce, optionnelle) — badges, fonds"
                valeur={couleurs.secondary}
                onChange={(v) => setCouleurs((c) => ({ ...c, secondary: v }))}
              />
              <CouleurSlot
                id="p3"
                label="Couleur 3 (accent, optionnelle) — liens"
                valeur={couleurs.accent}
                onChange={(v) => setCouleurs((c) => ({ ...c, accent: v }))}
              />
              <p className="club-note">
                Couleurs 2 et 3 : laissez le champ hexadécimal vide pour les
                retirer (une valeur dérivée de la couleur 1 est utilisée à la
                place).
              </p>

              <div className="club-identite-actions">
                <button
                  type="button"
                  className="club-file-btn"
                  disabled={themeEnCours}
                  onClick={() => void enregistrerIdentite()}
                >
                  {themeEnCours ? "Enregistrement…" : "Enregistrer l'identité"}
                </button>
              </div>
              {themeMsg && (
                <p className="club-err" role="alert">
                  {themeMsg}
                </p>
              )}
            </section>

            <section className="club-section" aria-labelledby="titre-coachs">
              <h2 id="titre-coachs" className="club-section-title">
                Coachs
              </h2>
              {coachsErr ? (
                <p className="club-err" role="alert">
                  {coachsErr}
                </p>
              ) : coachs.length > 0 ? (
                <ul className="coach-list">
                  {coachs.map((c) => (
                    <li key={c.nom} className="coach-row">
                      <span className="coach-name">{c.nom}</span>
                      {c.club && <span className="coach-club">{c.club}</span>}
                      {c.login ? (
                        <span className="club-badge">compte</span>
                      ) : (
                        <button
                          type="button"
                          className="chip-x"
                          aria-label={`Retirer ${c.nom}`}
                          onClick={() => void retirerCoach(c)}
                        >
                          ×
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="club-note">
                  Aucun coach pour l'instant : ajoutez les coachs sans compte en
                  bas de section.
                </p>
              )}
              <div className="coach-add-row">
                <input
                  type="text"
                  placeholder="Ajouter un coach par son nom"
                  value={nomCoach}
                  maxLength={80}
                  onChange={(e) => setNomCoach(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      void ajouterCoachNom();
                    }
                  }}
                />
                <button type="button" disabled={coachEnCours} onClick={() => void ajouterCoachNom()}>
                  Ajouter
                </button>
              </div>
              {coachMsg && (
                <p className="club-err" role="alert">
                  {coachMsg}
                </p>
              )}
            </section>

            <section className="club-section" aria-labelledby="titre-joueurs">
              <h2 id="titre-joueurs" className="club-section-title">
                Joueurs du club
              </h2>
              {joueursErr ? (
                <p className="club-err" role="alert">
                  {joueursErr}
                </p>
              ) : joueurs.length > 0 ? (
                <>
                  <p className="club-note">
                    Magasin du club, en lecture seule ici : le gestionnaire
                    ajoute et retire les joueurs, les coachs les lisent.
                    Prénom + nom uniquement (RGPD v1.1).
                  </p>
                  <div className="club-players">
                    {joueurs.map((nom) => (
                      <span key={nom} className="player-chip">
                        {nom}
                      </span>
                    ))}
                  </div>
                </>
              ) : (
                <p className="club-note">
                  Aucun joueur inscrit pour le club pour l'instant.
                </p>
              )}
            </section>

            {equipesErr ? (
              <p className="club-err" role="alert">
                {equipesErr}
              </p>
            ) : (
              sections.map(
                (s) =>
                  s.equipes.length > 0 && (
                    <section key={s.cat} className="club-section" aria-labelledby={`titre-${s.cat}`}>
                      <h2 id={`titre-${s.cat}`} className="club-section-title">
                        {s.cat}
                      </h2>
                      {s.equipes.map((eq) => (
                        <EquipeCard
                          key={eq.id}
                          eq={eq}
                          majEquipe={majEquipe(eq.id)}
                          preparer={() => preparer(eq)}
                        />
                      ))}
                    </section>
                  )
              )
            )}
          </>
        ) : (
          <p className="club-loading">Chargement…</p>
        )}
      </main>
    </div>
  );
}
