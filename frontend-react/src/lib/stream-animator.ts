/**
 * StreamAnimator — Smooth character-by-character text animation queue.
 *
 * HOW IT WORKS (ChatGPT-style smooth streaming):
 * ────────────────────────────────────────────────
 * 1. The SSE reader (stream.ts) receives text in irregular bursts from the LLM
 *    (e.g. "The average" then "ocean temperature" then "at 500m is").
 *
 * 2. Instead of dumping each burst into the UI immediately (which looks choppy),
 *    we push the text into a BUFFER (a queue of characters).
 *
 * 3. A requestAnimationFrame loop runs at ~60fps and pulls characters from the
 *    buffer ONE AT A TIME at a configurable speed (e.g. 30 chars per frame).
 *    This creates the smooth, consistent "typing" effect you see on ChatGPT.
 *
 * 4. When the user clicks "Stop", we call flush() to dump any remaining buffer
 *    instantly and stop the animation loop.
 *
 * USAGE:
 *   const animator = new StreamAnimator((text) => {
 *     store.appendAiAnswer(messageId, text);
 *   });
 *   animator.push("Hello ");       // called by SSE reader
 *   animator.push("world!");       // called by SSE reader
 *   animator.finish();             // called when SSE stream ends
 */
export class StreamAnimator {
  // Characters waiting to be rendered, stored as a simple string queue
  private buffer = "";

  // Whether the requestAnimationFrame loop is currently active
  private isAnimating = false;

  // The requestAnimationFrame ID (used to cancel the loop on stop/flush)
  private rafId: number | null = null;

  // Timestamp of the last character render (used to control speed)
  private lastRenderTime = 0;

  // Whether the SSE stream has finished sending all chunks
  private streamDone = false;

  // Callback that actually renders text into the UI (appends to Zustand store)
  private onRender: (text: string) => void;

  // Called when the entire buffer has been drained AND the stream is done
  private onComplete: (() => void) | null = null;

  // Speed: how many characters to render per animation frame (~16ms at 60fps).
  // Higher = faster typing. 3 chars/frame ≈ ~180 chars/sec which feels natural.
  private charsPerFrame: number;

  constructor(
    onRender: (text: string) => void,
    options?: { charsPerFrame?: number }
  ) {
    this.onRender = onRender;
    this.charsPerFrame = options?.charsPerFrame ?? 3;
  }

  /**
   * Push new text from the SSE reader into the animation buffer.
   * The animation loop will drain it smoothly.
   */
  push(text: string) {
    this.buffer += text;

    // Start the animation loop if it isn't running yet
    if (!this.isAnimating) {
      this.isAnimating = true;
      this.lastRenderTime = performance.now();
      this.tick();
    }
  }

  /**
   * Signal that the SSE stream is complete. The animator will keep running
   * until the buffer is fully drained, then call onComplete.
   */
  finish(onComplete?: () => void) {
    this.streamDone = true;
    this.onComplete = onComplete ?? null;

    // If buffer is already empty, complete immediately
    if (this.buffer.length === 0) {
      this.stop();
      this.onComplete?.();
    }
  }

  /**
   * Immediately dump all remaining buffered text into the UI and stop.
   * Used when the user clicks "Stop" — we don't want to lose partial text.
   */
  flush() {
    if (this.buffer.length > 0) {
      this.onRender(this.buffer);
      this.buffer = "";
    }
    this.stop();
  }

  /**
   * The core animation loop. Runs via requestAnimationFrame at ~60fps.
   * Each frame, it pulls `charsPerFrame` characters from the buffer
   * and passes them to onRender.
   */
  private tick = () => {
    if (!this.isAnimating) return;

    if (this.buffer.length > 0) {
      // Pull a small slice of characters from the front of the buffer
      const slice = this.buffer.slice(0, this.charsPerFrame);
      this.buffer = this.buffer.slice(this.charsPerFrame);

      // Render this slice into the UI (appends to the message bubble)
      this.onRender(slice);
    }

    // Check if we are done: stream finished AND buffer fully drained
    if (this.streamDone && this.buffer.length === 0) {
      this.stop();
      this.onComplete?.();
      return;
    }

    // Schedule the next frame
    this.rafId = requestAnimationFrame(this.tick);
  };

  /**
   * Stop the animation loop and cancel any pending frame.
   */
  private stop() {
    this.isAnimating = false;
    if (this.rafId !== null) {
      cancelAnimationFrame(this.rafId);
      this.rafId = null;
    }
  }
}
