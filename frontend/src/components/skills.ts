import { t } from '../i18n';

/** The skill a scenario trains (the key comes from the scenario pack). */
export const skillLabel = (key?: string): string | null => {
  const m: Record<string, string> = {
    prioritising: t('prioritising under pressure'), estimating: t('estimating and promising dates'),
    choosing: t('choosing between options'), changes: t('handling late changes'),
  };
  return key && m[key] ? m[key] : null;
};
