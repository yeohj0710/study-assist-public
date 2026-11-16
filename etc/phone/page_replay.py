"""촬영 쪽을 추적하고 완료된 풀이를 진동 대기열에 넣습니다."""

from collections import deque


class PageReplay:
    def __init__(self, frame_gap=6):
        self.frame_gap = frame_gap
        self.answers = {}
        self.numeric = set()
        self.confirmed = None
        self.candidate = None
        self.frames = 0
        self.last_frame_at = None
        self.waiting = deque()
        self.delivered = set()
        self.visit = 0
        self.active = None

    def observe(self, book, page, now):
        if book is None or page is None:
            self.candidate = None
            self.frames = 0
            self.last_frame_at = None
            return
        identity = (book, page)
        consecutive = (self.candidate == identity and self.last_frame_at is not None
                       and 0 < now - self.last_frame_at <= self.frame_gap)
        self.frames = min(self.frames + 1, 2) if consecutive else 1
        self.candidate = identity
        self.last_frame_at = now
        if self.frames == 2 and self.confirmed != identity:
            self.confirmed = identity
            self.visit += 1

    def save(self, book, pages, question, choice, *, numeric=False):
        valid_answer = type(choice) is int and (0 <= choice <= 999 if numeric else 1 <= choice <= 5)
        if not pages or not 1 <= question <= 999 or not valid_answer:
            raise ValueError('확정된 쪽과 유효한 문항번호, 보기 번호가 필요합니다.')
        key = (book, pages[0], question)
        if key not in self.answers:
            self.answers[key] = tuple(pages), choice
            self.waiting.append(key)
            if numeric:
                self.numeric.add(key)

    def ready_key(self):
        while self.waiting and self.waiting[0] in self.delivered:
            self.waiting.popleft()
        return self.waiting[0] if self.waiting else None

    def finished(self):
        if self.active is None:
            return
        key = self.active
        self.active = None
        self.delivered.add(key)
