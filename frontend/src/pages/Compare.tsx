import { Link } from 'react-router-dom';
import { t } from '../i18n';
import { PageHeader, Panel } from '../components/ui';

/** An honest comparison with a general chat assistant. No benchmarks: only what the product does and does not do. */
export default function ComparePage() {
  return (
    <div className="narrow">
      <PageHeader eyebrow={t('Compare')} title={t('RoleShift and a general chat assistant')} lead={t('You can ask a chat assistant the same question. Here is what is different, and what the assistant does better.')} />
      <Panel title={t('What RoleShift does differently')}>
        <ul className="plain">
          <li><b>{t('The numbers come from code.')}</b> {t('Dates, late days, costs and chances are calculated by fixed formulas on the figures you enter. A chat assistant may do the arithmetic wrong, and may answer differently each time.')}</li>
          <li><b>{t('The same inputs give the same output.')}</b> {t('You can change one number and see exactly what moves. Every formula is written down under "How was this calculated?".')}</li>
          <li><b>{t('You guess first.')}</b> {t('Before the result appears you can commit to a guess. Afterwards you see the gap, so you learn where your intuition and the numbers disagree.')}</li>
          <li><b>{t('Your decision is saved.')}</b> {t('The case, your reasoning, the document and your follow-up stay together, and Progress shows how often your guesses matched the calculator.')}</li>
          <li><b>{t('A document you can send.')}</b> {t('A priority proposal, an estimate reply or a decision note, built from your own numbers.')}</li>
        </ul>
      </Panel>
      <Panel title={t('What a chat assistant does better')}>
        <ul className="plain">
          <li>{t('It handles any situation, not only the few scenarios here.')}</li>
          <li>{t('It can ask you questions, explain the context and adjust the tone of a message to a specific person.')}</li>
          <li>{t('It copes with messy, incomplete information and free-form writing. Here you fill in fields.')}</li>
          <li>{t('It knows a lot about the world outside your numbers: laws, norms, how other teams work.')}</li>
        </ul>
      </Panel>
      <Panel title={t('Limits you should know')}>
        <ul className="plain">
          <li>{t('RoleShift only knows what you type. If an estimate is wrong, the result is wrong.')}</li>
          <li>{t('The risk labels and the quality rating are rules of thumb, not predictions or measurements.')}</li>
          <li>{t('Matching the calculator does not prove a decision was good in real life.')}</li>
        </ul>
        <p className="muted">{t('They work well together: calculate here, then paste the document into a chat assistant to polish the wording.')}</p>
        <p><Link to="/">{t('Back to the start')}</Link></p>
      </Panel>
    </div>
  );
}
