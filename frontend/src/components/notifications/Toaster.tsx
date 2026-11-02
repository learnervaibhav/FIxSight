import { AlertTriangle, CalendarCheck, CheckCircle2, MessageSquareText, Wrench, X } from 'lucide-react';
import { useLive } from '../../context/live';
import type { LiveEvent } from '../../types/api';
import { cn } from '../../lib/utils';

function toastStyle(event: LiveEvent) {
  if (event.type === 'notification') {
    const mock = event.data.status === 'mock_sent';
    return {
      icon: <MessageSquareText className="size-5" />,
      accent: mock ? 'border-l-blue-500 text-blue-600' : event.data.status === 'sent' ? 'border-l-emerald-500 text-emerald-600' : 'border-l-amber-500 text-amber-600',
      label: mock ? 'DEV · Mock SMS' : event.data.status === 'sent' ? 'SMS sent via Twilio' : `SMS ${String(event.data.status)}`,
    };
  }
  if (event.type === 'fault_detected') {
    return {
      icon: <AlertTriangle className="size-5" />,
      accent: event.severity === 'critical' ? 'border-l-red-500 text-red-600' : 'border-l-amber-500 text-amber-600',
      label: event.title,
    };
  }
  if (event.type === 'service_booked') return { icon: <CalendarCheck className="size-5" />, accent: 'border-l-blue-500 text-blue-600', label: event.title };
  if (event.type === 'service_completed') return { icon: <CheckCircle2 className="size-5" />, accent: 'border-l-emerald-500 text-emerald-600', label: event.title };
  return { icon: <Wrench className="size-5" />, accent: 'border-l-amber-500 text-amber-600', label: event.title };
}

export function Toaster() {
  const { toasts, dismissToast } = useLive();

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-[1200] flex w-[min(24rem,calc(100vw-2rem))] flex-col gap-2" aria-live="polite">
      {toasts.map(({ id, event }) => {
        const style = toastStyle(event);
        return (
          <div
            key={id}
            role="status"
            className={cn(
              'pointer-events-auto flex gap-3 rounded-lg border border-l-4 border-slate-200 bg-white p-3 shadow-lg animate-[toast-in_.25s_ease-out] dark:border-slate-700 dark:bg-slate-900',
              style.accent,
            )}
          >
            <div className="mt-0.5 shrink-0">{style.icon}</div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold uppercase tracking-wide">{style.label}</p>
              <p className="mt-1 whitespace-pre-line break-words text-sm text-slate-700 dark:text-slate-200">{event.message}</p>
            </div>
            <button type="button" aria-label="Dismiss" onClick={() => dismissToast(id)} className="h-fit rounded p-0.5 text-slate-400 hover:bg-slate-100 hover:text-slate-600 dark:hover:bg-slate-800">
              <X className="size-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
