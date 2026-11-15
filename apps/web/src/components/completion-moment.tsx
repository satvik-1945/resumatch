"use client";
import { useEffect, useRef } from "react";
import { SessionRecap } from "./session-recap";

export function CompletionMoment({ sessionId, onClose }: { sessionId: string; onClose: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialog.current!;
    if (!element.open) element.showModal();
    // No close listener here: React's dev double-mount would otherwise dismiss it instantly.
    return () => { element.close(); };
  }, []);
  function dismiss() { dialog.current?.close(); onClose(); }
  return <dialog ref={dialog} className="completion-dialog" aria-label="Run completed" onCancel={e => { e.preventDefault(); dismiss(); }} onClick={e => { if (e.target === e.currentTarget) dismiss(); }}>
    <button className="dialog-close icon-button" aria-label="Close celebration" onClick={dismiss}>×</button>
    <SessionRecap sessionId={sessionId} celebrate compact />
    <div className="completion-footer"><p>Saved to your private history.</p><button className="primary" autoFocus onClick={dismiss}>Continue to workspace <span aria-hidden="true">→</span></button></div>
  </dialog>;
}
