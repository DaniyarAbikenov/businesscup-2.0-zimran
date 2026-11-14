import { t } from '../i18n';

export interface TourStep { target: string; title: string; text: string }
export const TOUR_KEYS = ['home', 'form', 'guess', 'results', 'decided', 'progress', 'cases'] as const;
export type TourKey = (typeof TOUR_KEYS)[number];
const d = (k: string) => `[data-tour="${k}"]`;

/** Step definitions for every screen. A step whose target is not on the page is skipped. */
export const tours = (): Record<TourKey, TourStep[]> => ({
  home: [
    { target: d('home-heading'), title: t('What this is for'), text: t('Try your options with your own numbers before you commit, and get a ready message to send.') },
    { target: d('path'), title: t('Start with an exercise'), text: t('Pick the exercise that matches what you face. Start with the first one if you are not sure.') },
    { target: d('describe'), title: t('Or just describe it'), text: t('Write what is going on in your own words. We pick the exercise and fill in what you mention.') },
    { target: `${d('home-progress')}, ${d('nav-progress')}`, title: t('Come back to see your practice'), text: t('Here you see how often your guess matched the numbers, and what you have practised. It is a guide based on what you entered, not a test.') },
  ],
  form: [
    { target: d('stepper'), title: t('Four steps'), text: t('Fill in, compare, decide, follow up. You are on the first one.') },
    { target: d('form-steps'), title: t('A few short steps'), text: t('The form is split into steps. Use Next and Back, and check everything on the last step before you compare.') },
    { target: d('form-live'), title: t('Where this stands'), text: t('This panel updates while you type. It shows what the numbers imply so far and what is still missing. Nothing is saved.') },
    { target: d('form-first'), title: t('Use your own numbers'), text: t('Rounded or made-up numbers are fine. Do not enter confidential data.') },
    { target: d('form-why'), title: t('Why we ask'), text: t('Tap "Why we ask" under a field to see why it matters for the result.') },
    { target: d('form-forgot'), title: t('Did I forget anything?'), text: t('Unwritten hours and promises are what break plans. Open this and add what you may be missing.') },
    { target: d('form-submit'), title: t('Compare my options'), text: t('When the numbers look right, continue. You can change them later.') },
  ],
  guess: [
    { target: d('guess-controls'), title: t('Guess first'), text: t('Before you see the numbers, say what you expect. You learn more this way, and it takes ten seconds.') },
    { target: d('guess-skip'), title: t('You can skip'), text: t('Skip the guess any time and go straight to the numbers.') },
  ],
  results: [
    { target: d('res-best'), title: t('The answer first'), text: t('One sentence from the numbers, before the details. The decision is still yours.') },
    { target: d('res-guess'), title: t('Your guess vs the numbers'), text: t('What you expected next to what the calculation says, and what was not counted.') },
    { target: d('res-ledger'), title: t('How to read this'), text: t('Each column is one option. Read down: dates, costs or lateness, then what to watch.') },
    { target: d('res-levers'), title: t('Time, money, quality'), text: t('Every way to fix lateness costs something. This table shows what each way costs in time, money and quality.') },
    { target: d('res-why'), title: t('Risk on your numbers'), text: t('This is a calculation on your numbers, not a forecast. "Why this label" shows how it was made.') },
    { target: d('res-whatif'), title: t('What if?'), text: t('Drag a number to see how the answer changes. Nothing is saved until you press Save these numbers.') },
    { target: d('res-challenge'), title: t('Challenge my numbers'), text: t('Recalculates with worse numbers to see if the conclusion still holds.') },
    { target: d('res-choose'), title: t('Decide'), text: t('Choose one option, say why, and you get a ready message or document.') },
  ],
  decided: [
    { target: d('dec-doc'), title: t('Your document'), text: t('Edit it, copy or download it, then send it. Your changes are saved with the case.') },
    { target: d('dec-followup'), title: t('Come back and tell us'), text: t('We remind you on the follow-up date. Recording how it went is what makes your progress real.') },
  ],
  progress: [
    { target: d('pr-bar'), title: t('Your first 90 days'), text: t('Where you are in the first three months, with markers at 30, 60 and 90.') },
    { target: d('pr-skills'), title: t('Your intuition vs the numbers'), text: t('How often your guess matched the calculation, per skill. A trend appears after three guesses.') },
    { target: d('pr-timeline'), title: t('Decisions and outcomes'), text: t('Every case, with what you chose and how it turned out, as you reported it.') },
    { target: d('pr-reminders'), title: t('Email reminders'), text: t('Optional. We email you when a follow-up is due, never your numbers.') },
  ],
  cases: [
    { target: d('cases-tabs'), title: t('Journal and documents'), text: t('Your timeline and every document you saved live here. Switch with the tabs.') },
  ],
});
