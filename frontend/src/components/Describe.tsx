import { t } from '../i18n';
import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSession } from '../App';
import { Intake, api } from '../api';
import { log } from '../log';
import { Button, Field, Panel } from './ui';

/** "Describe your scenario": free text -> the matching scenario with the form pre-filled. Nothing is saved here. */
export default function Describe() {
  const { me, pack } = useSession();
  const example = pack.roles.find((r) => r.id === me.profile?.roleId)?.describeExample;
  const nav = useNavigate();
  const [text, setText] = useState('');
  const [useAi, setUseAi] = useState(me.llmEnabled);
  const [ack, setAck] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError('');
    if (text.trim().length < 20) { setError(t('Write a few sentences (at least 20 characters).')); return; }
    if (useAi && !ack) { setError(t('Confirm there is no confidential information, or turn off AI reading.')); return; }
    setBusy(true);
    try {
      const r = await api<Intake>('POST', '/intake', { text, useAi, privacyAck: ack });
      log.info('intake.done', r.source, { situation: r.situationId, filled: r.filled.length });
      nav(`/new/${r.situationId}`, { state: { intake: r, text } });
    } catch (x: any) {
      setError(x.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Panel title={t('Describe your scenario')} lead={t('Not sure which one fits? Write what is going on in your own words. We pick the scenario and fill in what you mention. You review everything before anything is calculated or saved.')}>
      <form onSubmit={submit} noValidate>
        <Field id="describe" label={t('What is going on?')} help={t('Who asked for what, by when, how much time you have. Leave out names of clients and your employer.')}>
          {(a) => <textarea className="input" rows={5} maxLength={4000} {...a} value={text} onChange={(e) => setText(e.target.value)}
            placeholder={example || t('My manager wants the quarterly report by Friday, a colleague needs a data pull for a client demo on Wednesday, and the VP asked me for an overview next week. I have about 25 free hours.')} />}
        </Field>
        <div className="small muted">{text.length} / 4000</div>
        {me.llmEnabled ? (
          <>
            <label className="check"><input type="checkbox" checked={useAi} onChange={(e) => setUseAi(e.target.checked)} /> {t('Let AI read the text and fill in numbers and dates (the text is sent to our AI provider, Anthropic, and not stored by us)')}</label>
            {useAi && <label className="check"><input type="checkbox" checked={ack} onChange={(e) => setAck(e.target.checked)} /> {t('I did not include confidential employer or client information.')}</label>}
          </>
        ) : <p className="small muted">{t('AI reading is off on this server. We match your text by keywords and copy it into the form; you enter the numbers.')}</p>}
        {error && <div className="field error" role="alert">{error}</div>}
        <div className="row" style={{ marginTop: 16 }}><Button type="submit" busy={busy}>{t('Find my scenario')}</Button></div>
      </form>
    </Panel>
  );
}
