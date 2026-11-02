import { useEffect, useRef, useState } from 'react';
import { ChevronDown, FlaskConical, Pause, Play, RotateCcw, Send, SkipForward } from 'lucide-react';
import { useLive } from '../../context/live';
import { api } from '../../lib/api';
import type { SimulationMode, TwilioCheck } from '../../types/api';
import { cn, formatDateTime } from '../../lib/utils';

const SPEEDS = [
  { label: 'Fast', seconds: 1.5 },
  { label: 'Normal', seconds: 3 },
  { label: 'Slow', seconds: 6 },
];

export function SimulationControl() {
  const { status, busy, start, stop, reset, step, actionError, backendOnline } = useLive();
  const [open, setOpen] = useState(false);
  const [confirmReal, setConfirmReal] = useState(false);
  const [speed, setSpeed] = useState(3);
  const [twilioCheck, setTwilioCheck] = useState<TwilioCheck | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  const running = status?.running ?? false;
  const mode = status?.mode ?? 'mock';
  const twilioReady = status?.twilio_configured ?? false;

  useEffect(() => {
    if (!open) return;
    const onClick = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
        setConfirmReal(false);
      }
    };
    const onKey = (event: KeyboardEvent) => event.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  // Read-only Twilio diagnosis each time the menu opens, so Real-mode problems show before starting.
  useEffect(() => {
    if (!open || !twilioReady) return;
    let cancelled = false;
    api.twilioCheck().then(
      (result) => !cancelled && setTwilioCheck(result),
      () => !cancelled && setTwilioCheck(null),
    );
    return () => {
      cancelled = true;
    };
  }, [open, twilioReady]);

  const launch = async (selected: SimulationMode) => {
    if (selected === 'real' && !confirmReal) {
      setConfirmReal(true);
      return;
    }
    setOpen(false);
    setConfirmReal(false);
    await start(selected, { tick_seconds: speed });
  };

  return (
    <div className="relative flex items-center gap-2" ref={menuRef}>
      {running && (
        <div className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-1.5 text-xs md:flex dark:border-slate-700 dark:bg-slate-800/60">
          <span className="relative flex size-2">
            <span className={cn('absolute inline-flex size-full animate-ping rounded-full opacity-75', mode === 'real' ? 'bg-red-500' : 'bg-emerald-500')} />
            <span className={cn('relative inline-flex size-2 rounded-full', mode === 'real' ? 'bg-red-500' : 'bg-emerald-500')} />
          </span>
          <span className="font-semibold uppercase tracking-wide text-slate-700 dark:text-slate-200">{mode === 'real' ? 'Live · Real SMS' : 'Live · Mock'}</span>
          <span className="text-slate-400">|</span>
          <span className="tabular-nums text-slate-600 dark:text-slate-300">Round {status?.round ?? 0}</span>
          <span className="text-slate-400">|</span>
          <span className="tabular-nums text-slate-600 dark:text-slate-300">{formatDateTime(status?.sim_time)}</span>
        </div>
      )}

      <div className="inline-flex overflow-hidden rounded-lg shadow-sm">
        {running ? (
          <button
            type="button"
            onClick={() => void stop()}
            disabled={busy}
            className="inline-flex items-center gap-1.5 bg-slate-800 px-3.5 py-2 text-sm font-medium text-white hover:bg-slate-900 disabled:opacity-60 dark:bg-slate-700 dark:hover:bg-slate-600"
          >
            <Pause className="size-4" /> Stop simulation
          </button>
        ) : (
          <button
            type="button"
            onClick={() => setOpen((value) => !value)}
            disabled={busy || !backendOnline}
            className="inline-flex items-center gap-1.5 bg-blue-600 px-3.5 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
          >
            <Play className="size-4" /> Simulation
          </button>
        )}
        <button
          type="button"
          aria-label="Simulation options"
          aria-expanded={open}
          onClick={() => setOpen((value) => !value)}
          disabled={!backendOnline}
          className={cn(
            'border-l px-2 text-white disabled:opacity-60',
            running ? 'border-slate-600 bg-slate-800 hover:bg-slate-900 dark:bg-slate-700' : 'border-blue-500 bg-blue-600 hover:bg-blue-700',
          )}
        >
          <ChevronDown className="size-4" />
        </button>
      </div>

      {open && (
        <div className="absolute right-0 top-full z-[1100] mt-2 w-80 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl dark:border-slate-700 dark:bg-slate-900">
          <div className="border-b border-slate-100 px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-slate-500 dark:border-slate-800">
            {running ? 'Switch mode' : 'Start simulation'}
          </div>

          <button
            type="button"
            onClick={() => void launch('real')}
            disabled={!twilioReady}
            className={cn(
              'flex w-full items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50 dark:hover:bg-slate-800',
              running && mode === 'real' && 'bg-red-50/60 dark:bg-red-950/30',
            )}
          >
            <Send className="mt-0.5 size-4 shrink-0 text-red-500" />
            <span>
              <span className="block text-sm font-medium text-slate-900 dark:text-white">Simulation – Real</span>
              <span className="block text-xs text-slate-500 dark:text-slate-400">
                {twilioReady
                  ? confirmReal
                    ? `Click again to confirm. Sends real SMS via Twilio (max ${status?.sms_limit ?? 10} per run).`
                    : 'Uses your Twilio API key to send real SMS alerts.'
                  : 'Twilio is not configured (TWILIO_* and ALERT_SMS_TO in .env).'}
              </span>
              {twilioReady && twilioCheck && !twilioCheck.ok && (
                <span className="mt-1.5 block space-y-1 rounded-md bg-red-50 px-2 py-1.5 text-[11px] leading-snug text-red-700 dark:bg-red-950/60 dark:text-red-300">
                  <b className="block">SMS will fail with the current Twilio setup:</b>
                  {twilioCheck.issues.map((issue) => (
                    <span key={issue} className="block">• {issue}</span>
                  ))}
                </span>
              )}
              {twilioReady && twilioCheck?.ok && (
                <span className="mt-1 block text-[11px] text-emerald-600">Twilio check passed · sender {twilioCheck.sender} → {twilioCheck.recipient}</span>
              )}
            </span>
          </button>

          <button
            type="button"
            onClick={() => void launch('mock')}
            className={cn(
              'flex w-full items-start gap-3 border-t border-slate-100 px-4 py-3 text-left transition-colors hover:bg-slate-50 dark:border-slate-800 dark:hover:bg-slate-800',
              running && mode === 'mock' && 'bg-emerald-50/60 dark:bg-emerald-950/30',
            )}
          >
            <FlaskConical className="mt-0.5 size-4 shrink-0 text-emerald-500" />
            <span>
              <span className="block text-sm font-medium text-slate-900 dark:text-white">Simulation – Mock</span>
              <span className="block text-xs text-slate-500 dark:text-slate-400">No SMS is sent. Alerts appear as in-app dev notifications.</span>
            </span>
          </button>

          <div className="space-y-3 border-t border-slate-100 bg-slate-50 px-4 py-3 dark:border-slate-800 dark:bg-slate-950/40">
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs text-slate-500">Speed</span>
              <div className="inline-flex rounded-md border border-slate-200 bg-white p-0.5 dark:border-slate-700 dark:bg-slate-900">
                {SPEEDS.map((option) => (
                  <button
                    key={option.label}
                    type="button"
                    onClick={() => setSpeed(option.seconds)}
                    className={cn(
                      'rounded px-2 py-0.5 text-xs',
                      speed === option.seconds ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800',
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => void step()}
                disabled={running || busy}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              >
                <SkipForward className="size-3.5" /> Step one tick
              </button>
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  void reset();
                }}
                disabled={busy}
                className="inline-flex flex-1 items-center justify-center gap-1 rounded-md border border-slate-200 bg-white px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-100 disabled:opacity-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200"
              >
                <RotateCcw className="size-3.5" /> Reset
              </button>
            </div>
            {!status?.llm_configured && <p className="text-[11px] text-slate-500">GOOGLE_API_KEY not set: AI explanations use rule-based text.</p>}
          </div>
        </div>
      )}

      {actionError && !open && (
        <div className="absolute right-0 top-full z-[1100] mt-2 w-72 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 shadow dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {actionError}
        </div>
      )}
    </div>
  );
}
