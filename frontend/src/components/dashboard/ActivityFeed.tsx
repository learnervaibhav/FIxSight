import { AlertTriangle, CalendarCheck, CheckCircle2, Info, MessageSquareText, PlayCircle, Wrench } from 'lucide-react';
import type { LiveEvent } from '../../types/api';
import { cn, formatTime } from '../../lib/utils';
import { EmptyState } from '../ui/primitives';

const ICONS: Record<string, typeof Info> = {
  fault_detected: AlertTriangle,
  service_booked: CalendarCheck,
  service_started: Wrench,
  service_active: Wrench,
  service_completed: CheckCircle2,
  notification: MessageSquareText,
  simulation: PlayCircle,
};

const COLORS: Record<LiveEvent['severity'], string> = {
  critical: 'text-red-600 bg-red-50 dark:bg-red-950/60',
  warning: 'text-amber-600 bg-amber-50 dark:bg-amber-950/60',
  success: 'text-emerald-600 bg-emerald-50 dark:bg-emerald-950/60',
  info: 'text-blue-600 bg-blue-50 dark:bg-blue-950/60',
};

export function ActivityFeed({ events, limit = 40 }: { events: LiveEvent[]; limit?: number }) {
  const items = [...events].reverse().slice(0, limit);
  if (!items.length) {
    return <EmptyState icon={<PlayCircle className="size-8" />} title="No activity yet" description="Start a simulation to stream telemetry through the AI pipeline." />;
  }
  return (
    <ol className="divide-y divide-slate-100 dark:divide-slate-800">
      {items.map((event) => {
        const Icon = ICONS[event.type] ?? Info;
        return (
          <li key={event.id} className="flex gap-3 px-5 py-3">
            <div className={cn('mt-0.5 h-fit rounded-md p-1.5', COLORS[event.severity])}>
              <Icon className="size-3.5" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-baseline justify-between gap-2">
                <p className="truncate text-sm font-medium text-slate-800 dark:text-slate-100">{event.title}</p>
                <time className="shrink-0 text-[11px] tabular-nums text-slate-400">{formatTime(event.created_at)}</time>
              </div>
              <p className="mt-0.5 line-clamp-3 whitespace-pre-line text-xs text-slate-500 dark:text-slate-400">{event.message}</p>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
