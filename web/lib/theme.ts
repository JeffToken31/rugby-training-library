// Lot peaufinage B (2026-11-25) — identité du club : le serveur (PUT
// /api/club/theme) stocke couleurs + logo ; ce fichier dérive les variables
// CSS et les applique à toute la surface de l'app (v2-cadrage §3.4, option A).
// Repli : club sans identité → aucune variable posée, thème par défaut intact.

export interface ClubTheme {
  couleurs: {
    /** Couleur principale (obligatoire) : boutons, focus, liens d'action. */
    primary: string;
    /** Fond doux (badges, chips) — optionnelle, dérivée sinon. */
    secondary: string | null;
    /** Accent des liens — optionnelle, absente = liens sans couleur propre. */
    accent: string | null;
  };
  /** Logo en data URI (PNG ou SVG), ou null si le club n'en a pas. */
  logo: string | null;
}

const INK_SOMBRE = "#101216";
const FOND_CLAIR = "#ffffff";
const FOND_SOMBRE = "#101216";

function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace("#", "");
  return [
    parseInt(h.slice(0, 2), 16),
    parseInt(h.slice(2, 4), 16),
    parseInt(h.slice(4, 6), 16),
  ];
}

/** Mélange de deux couleurs hex : t = part de `b` (0..1). */
function mix(a: string, b: string, t: number): string {
  const [ar, ag, ab] = hexToRgb(a);
  const [br, bg, bb] = hexToRgb(b);
  const c = (x: number, y: number) =>
    Math.round(x + (y - x) * t)
      .toString(16)
      .padStart(2, "0");
  return `#${c(ar, br)}${c(ag, bg)}${c(ab, bb)}`;
}

/** Luminance relative (0 = noir, 1 = blanc), pour choisir l'encre posée. */
function luminance(hex: string): number {
  const [r, g, b] = hexToRgb(hex).map((v) => v / 255);
  const f = (c: number) => (c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4));
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}

/** Encre lisible sur le primaire : encre sombre si la couleur est claire. */
export function enrePour(fond: string): string {
  return luminance(fond) >= 0.5 ? INK_SOMBRE : "#ffffff";
}

/** Fond doux dérivé du primaire, teinté du fond de l'app (clair ou sombre). */
function douxPour(fond: string, themeSombre: boolean): string {
  return themeSombre ? mix(fond, FOND_SOMBRE, 0.8) : mix(fond, FOND_CLAIR, 0.85);
}

/**
 * Applique l'identité du club actif à toute la surface de l'app : variables
 * CSS inline sur <html> (elles priment sur les blocs :root et
 * [data-theme="dark"] — le thème du club suit donc le thème clair/sombre).
 * `theme` null = retirer les variables (repli au thème par défaut).
 */
export function appliquerThemeClub(theme: ClubTheme | null): void {
  const style = document.documentElement.style;
  if (theme === null) {
    for (const nom of [
      "--accent",
      "--focus",
      "--accent-ink",
      "--accent-soft",
      "--club-accent",
    ]) {
      style.removeProperty(nom);
    }
    return;
  }
  const sombre = document.documentElement.dataset.theme === "dark";
  const primary = theme.couleurs.primary;
  style.setProperty("--accent", primary);
  style.setProperty("--focus", primary);
  style.setProperty("--accent-ink", enrePour(primary));
  style.setProperty(
    "--accent-soft",
    theme.couleurs.secondary ?? douxPour(primary, sombre)
  );
  if (theme.couleurs.accent) {
    style.setProperty("--club-accent", theme.couleurs.accent);
  } else {
    style.removeProperty("--club-accent");
  }
}
