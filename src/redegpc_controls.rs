/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */
//! Degeneration's desktop actions expressed as logical 480×320 screen touches.
//!
//! These coordinates start with the inherited Degeneration controller profile.
//! Keeping the state machine independent of SDL makes aliases, focus loss and
//! simultaneous actions testable without running the guest.

use std::collections::VecDeque;
use std::time::{Duration, Instant};

pub(crate) type Coords = (f32, f32);

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
#[repr(usize)]
pub(crate) enum Input {
    W,
    A,
    S,
    D,
    Up,
    Left,
    Down,
    Right,
    Aim,
    Fire,
    Reload,
    Shake,
    Interact,
    Inventory,
    Pause,
}

const INPUT_COUNT: usize = Input::Pause as usize + 1;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Hash)]
#[repr(usize)]
pub enum Action {
    Movement,
    Aim,
    Primary,
    Inventory,
    Pause,
}

const ACTIONS: [Action; 5] = [
    Action::Movement,
    Action::Aim,
    Action::Primary,
    Action::Inventory,
    Action::Pause,
];

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) enum Phase {
    Down,
    Move,
    Up,
}

#[derive(Clone, Copy, Debug, PartialEq)]
pub(crate) struct Touch {
    pub action: Action,
    pub phase: Phase,
    pub coords: Coords,
}

#[derive(Default)]
pub(crate) struct Controls {
    held: [bool; INPUT_COUNT],
    touches: [Option<Coords>; ACTIONS.len()],
    reload_started: Option<Instant>,
    shake_started: Option<Instant>,
    menu_page: Option<u8>,
    navigation: VecDeque<(Instant, Touch)>,
    navigation_touch: Option<Coords>,
    aim_pulses: VecDeque<(Instant, Touch)>,
    aim_touch: Option<Coords>,
    aim_mode: bool,
    mouse_pending: Coords,
    mouse_velocity: Coords,
    mouse_polled: Option<Instant>,
}

impl Controls {
    /// Raw desktop mouse input must never activate the hidden gameplay pad,
    /// aim/fire or knife buttons. The phone remains a visible click target.
    /// Title screens and phone menus retain their ordinary pointer interface.
    pub fn allows_pointer_click(gameplay: bool, (x, y): Coords) -> bool {
        (0.0..480.0).contains(&x)
            && (0.0..320.0).contains(&y)
            && (!gameplay || x < 60.0 && y < 64.0)
    }

    /// A menu may close on mouse-down before its mouse-up reaches us. The
    /// rendered gameplay HUD is authoritative when returning from that menu.
    pub fn entered_gameplay(&mut self) {
        self.menu_page = None;
    }

    pub fn is_held(&self, input: Input) -> bool {
        self.held[input as usize]
    }

    /// Holding two aliases is one action; opposite directions cancel. Repeats
    /// and duplicate release events never introduce additional guest touches.
    pub fn set(&mut self, input: Input, pressed: bool) -> Vec<Touch> {
        let edge = pressed && !self.is_held(input);
        if input == Input::Aim && self.menu_page.is_none() {
            if edge && !self.aim_mode {
                self.aim_mode = true;
                self.queue_aim_tap((440.0, 200.0), Instant::now());
            } else if !pressed && self.is_held(input) {
                self.end_aim(Instant::now());
                self.held[Input::Fire as usize] = false;
            }
        }
        if edge && matches!(input, Input::Inventory | Input::Pause) && self.navigation.is_empty() {
            self.navigate(input, Instant::now());
        }
        if input == Input::Reload && pressed && !self.is_held(input) {
            self.reload_started = Some(Instant::now());
        }
        if input == Input::Shake {
            if edge {
                self.shake_started = Some(Instant::now());
            } else if !pressed {
                self.shake_started = None;
            }
        }
        self.held[input as usize] = pressed;
        let mut events = self.update();
        events.extend(self.poll());
        events
    }

    /// Release at each touch's last position, including movement. SDL may omit
    /// key-up and mouse-up events when the window loses keyboard focus.
    pub fn clear(&mut self) -> Vec<Touch> {
        self.held.fill(false);
        self.reload_started = None;
        self.shake_started = None;
        self.reset_mouse_look();
        self.navigation.clear();
        let mut events = self.update();
        if let Some(coords) = self.navigation_touch.take() {
            events.push(Touch {
                action: Action::Inventory,
                phase: Phase::Up,
                coords,
            });
            self.observe_pointer_click(coords);
        }
        self.aim_pulses.clear();
        if let Some(coords) = self.aim_touch.take() {
            events.push(Touch {
                action: Action::Aim,
                phase: Phase::Up,
                coords,
            });
        }
        self.aim_mode = false;
        events
    }

    pub fn clear_on_focus_loss(&mut self) -> Vec<Touch> {
        let exit_needed = self.aim_mode
            || self
                .aim_pulses
                .iter()
                .any(|(_, t)| t.coords == (440.0, 100.0));
        let events = self.clear();
        if exit_needed {
            self.queue_aim_tap((440.0, 100.0), Instant::now());
        }
        events
    }

    pub fn captures_mouse(&self) -> bool {
        self.is_held(Input::Aim) && self.menu_page.is_none()
    }

    /// Accumulate relative desktop motion, then spend it at the guest's original
    /// control-pad speed. A fast flick is bounded without discarding its travel.
    pub fn mouse_motion(&mut self, dx: i32, dy: i32) {
        if self.captures_mouse() {
            self.mouse_pending.0 = (self.mouse_pending.0 + dx as f32).clamp(-1200.0, 1200.0);
            self.mouse_pending.1 = (self.mouse_pending.1 + dy as f32).clamp(-1200.0, 1200.0);
        }
    }

    fn reset_mouse_look(&mut self) {
        self.mouse_pending = (0.0, 0.0);
        self.mouse_velocity = (0.0, 0.0);
        self.mouse_polled = None;
    }

    fn poll_mouse_look(&mut self, now: Instant) {
        if !self.captures_mouse() {
            self.reset_mouse_look();
            return;
        }
        if !self.aim_pulses.is_empty() {
            self.mouse_polled = Some(now);
            self.mouse_velocity = (0.0, 0.0);
            return;
        }
        let elapsed = self.mouse_polled.replace(now).map_or(0.0, |last| {
            now.saturating_duration_since(last).as_secs_f32().min(0.05)
        });
        if elapsed <= 0.0 {
            return;
        }
        // 600 desktop pixels correspond to one second of full pad travel.
        let budget = 600.0 * elapsed;
        self.mouse_velocity = (
            (self.mouse_pending.0 / budget).clamp(-1.0, 1.0),
            (self.mouse_pending.1 / budget).clamp(-1.0, 1.0),
        );
        self.mouse_pending.0 -= self.mouse_velocity.0 * budget;
        self.mouse_pending.1 -= self.mouse_velocity.1 * budget;
    }

    fn queue_aim_tap(&mut self, coords: Coords, now: Instant) {
        self.aim_pulses.push_back((
            now,
            Touch {
                action: Action::Aim,
                phase: Phase::Down,
                coords,
            },
        ));
        self.aim_pulses.push_back((
            now + Duration::from_millis(50),
            Touch {
                action: Action::Aim,
                phase: Phase::Up,
                coords,
            },
        ));
    }
    fn end_aim(&mut self, now: Instant) {
        self.reset_mouse_look();
        self.aim_pulses.clear();
        let next = if let Some(coords) = self.aim_touch {
            self.aim_pulses.push_back((
                now,
                Touch {
                    action: Action::Aim,
                    phase: Phase::Up,
                    coords,
                },
            ));
            now + Duration::from_millis(50)
        } else {
            now
        };
        self.queue_aim_tap((440.0, 100.0), next);
        self.aim_mode = false;
    }

    /// Menu navigation is normal guest touch input, with separate frames for
    /// press/release and page changes. The phone always opens on Map in v1.03.
    fn navigate(&mut self, input: Input, mut now: Instant) {
        if self.aim_mode {
            self.end_aim(now);
            now += Duration::from_millis(200);
        }
        self.shake_started = None;
        for input in [
            Input::Shake,
            Input::W,
            Input::A,
            Input::S,
            Input::D,
            Input::Up,
            Input::Left,
            Input::Down,
            Input::Right,
            Input::Aim,
            Input::Fire,
            Input::Interact,
        ] {
            self.held[input as usize] = false;
        }
        let mut taps = Vec::new();
        match (input, self.menu_page) {
            (Input::Pause, Some(_)) | (Input::Inventory, Some(1)) => taps.push((25.0, 300.0)),
            (Input::Pause, None) => taps.push((30.0, 30.0)),
            (Input::Inventory, page) => {
                if page.is_some() {
                    taps.push((25.0, 300.0));
                }
                taps.extend([(30.0, 30.0), (455.0, 23.0)]);
            }
            _ => return,
        }
        for (i, coords) in taps.into_iter().enumerate() {
            let start = now + Duration::from_millis(i as u64 * 120);
            self.navigation.push_back((
                start,
                Touch {
                    action: Action::Inventory,
                    phase: Phase::Down,
                    coords,
                },
            ));
            self.navigation.push_back((
                start + Duration::from_millis(50),
                Touch {
                    action: Action::Inventory,
                    phase: Phase::Up,
                    coords,
                },
            ));
        }
    }

    pub fn poll(&mut self) -> Vec<Touch> {
        self.poll_at(Instant::now())
    }
    fn poll_at(&mut self, now: Instant) -> Vec<Touch> {
        self.poll_mouse_look(now);
        let mut events = self.update();
        if self.aim_pulses.front().is_some_and(|(due, _)| *due <= now) {
            let (due, touch) = self.aim_pulses.pop_front().unwrap();
            let late = now.saturating_duration_since(due);
            for (due, _) in &mut self.aim_pulses {
                *due += late;
            }
            self.aim_touch = if touch.phase == Phase::Down {
                Some(touch.coords)
            } else {
                None
            };
            events.push(touch);
        }
        if self.navigation.front().is_some_and(|(due, _)| *due <= now) {
            let (due, touch) = self.navigation.pop_front().unwrap();
            let late = now.saturating_duration_since(due);
            for (due, _) in &mut self.navigation {
                *due += late;
            }
            if touch.phase == Phase::Down {
                self.navigation_touch = Some(touch.coords);
            } else {
                self.navigation_touch = None;
                self.observe_pointer_click(touch.coords);
            }
            events.push(touch);
        }
        events
    }

    /// Keep keyboard navigation aligned when the user clicks the phone, its
    /// page arrows, back button, or Resume Game with the pointer.
    pub fn observe_pointer_click(&mut self, (x, y): Coords) {
        if let Some(page) = self.menu_page {
            if x < 60.0 && y > 270.0
                || page == 4 && (90.0..430.0).contains(&x) && (248.0..287.0).contains(&y)
            {
                self.menu_page = None;
            } else if y < 50.0 && x > 430.0 {
                self.menu_page = Some((page + 1) % 5);
            } else if y < 50.0 && x < 50.0 {
                self.menu_page = Some((page + 4) % 5);
            }
        } else if x < 60.0 && y < 60.0 {
            self.menu_page = Some(0);
        }
    }

    /// The supplied English tutorial specifies tipping the screen forward
    /// and back to reload. Its console configuration requires a dot product
    /// above 3100/4096 along Airplay's landscape X. The guest's accelerometer
    /// callback rotates UIKit's portrait axes before applying that test.
    /// Two opposite 60-degree tips exceed
    /// that threshold without changing the guest's clock or event scheduling.
    pub fn reload_acceleration(&self) -> Option<(f32, f32, f32)> {
        let elapsed = self.reload_started?.elapsed();
        reload_acceleration_at(elapsed)
    }

    /// Hold Space to shake off a grab. This is translational acceleration,
    /// unlike R's gravity-only reload tilt. Both axes are exercised so the
    /// landscape transform preserves a physical shake in the guest callback.
    pub fn shake_acceleration(&self) -> Option<(f32, f32, f32)> {
        self.shake_started
            .map(|started| shake_acceleration_at(started.elapsed()))
    }

    fn update(&mut self) -> Vec<Touch> {
        let held = |input| self.is_held(input);
        let horizontal = i32::from(held(Input::D) || held(Input::Right))
            - i32::from(held(Input::A) || held(Input::Left));
        let vertical = i32::from(held(Input::S) || held(Input::Down))
            - i32::from(held(Input::W) || held(Input::Up));
        let horizontal = (horizontal as f32 + self.mouse_velocity.0).clamp(-1.0, 1.0);
        let vertical = (vertical as f32 + self.mouse_velocity.1).clamp(-1.0, 1.0);
        let movement = if horizontal == 0.0 && vertical == 0.0 {
            None
        } else {
            // Rectangle from touchHLE's Degeneration profile: 25,200,95,100.
            Some((72.5 + horizontal * 47.5, 250.0 + vertical * 50.0))
        };
        let next = [
            movement,
            None,
            (held(Input::Fire) || held(Input::Interact)).then_some((440.0, 200.0)),
            None,
            None,
        ];
        let mut events = Vec::new();
        for (index, action) in ACTIONS.into_iter().enumerate() {
            if action == Action::Movement && self.touches[index].is_none() && next[index].is_some()
            {
                events.push(Touch {
                    action,
                    phase: Phase::Down,
                    coords: (72.5, 250.0),
                });
                events.push(Touch {
                    action,
                    phase: Phase::Move,
                    coords: next[index].unwrap(),
                });
                continue;
            }
            let event = match (self.touches[index], next[index]) {
                (None, Some(coords)) => Some((Phase::Down, coords)),
                (Some(coords), None) => Some((Phase::Up, coords)),
                (Some(old), Some(new)) if old != new => Some((Phase::Move, new)),
                _ => None,
            };
            if let Some((phase, coords)) = event {
                events.push(Touch {
                    action,
                    phase,
                    coords,
                });
            }
        }
        self.touches = next;
        events
    }
}

fn shake_acceleration_at(elapsed: Duration) -> (f32, f32, f32) {
    let direction = if (elapsed.as_millis() / 40).is_multiple_of(2) {
        1.0
    } else {
        -1.0
    };
    (direction * 2.0, -direction * 2.0, -1.0)
}

fn reload_acceleration_at(elapsed: Duration) -> Option<(f32, f32, f32)> {
    let direction = if elapsed < Duration::from_millis(120) {
        1.0
    } else if elapsed < Duration::from_millis(240) {
        -1.0
    } else {
        return None;
    };
    Some((direction * 3.0_f32.sqrt() / 2.0, 0.0, -0.5))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn menu_closing_before_mouse_release_does_not_disable_mapped_aim() {
        let mut controls = Controls::default();
        controls.observe_pointer_click((30.0, 30.0));
        controls.observe_pointer_click((455.0, 23.0));
        assert_eq!(controls.menu_page, Some(1));
        controls.entered_gameplay();
        assert_eq!(controls.menu_page, None);
        let touches = controls.set(Input::Aim, true);
        assert!(touches
            .iter()
            .any(|t| t.action == Action::Aim && t.phase == Phase::Down));
        controls.set(Input::Aim, false);
        assert!(!controls.captures_mouse());
    }

    #[test]
    fn gameplay_mouse_cannot_reach_pad_or_actions_but_phone_and_menus_work() {
        for coords in [
            (72.5, 250.0),
            (25.0, 200.0),
            (120.0, 300.0),
            (440.0, 100.0),
            (440.0, 200.0),
            (440.0, 280.0),
            (240.0, 160.0),
        ] {
            assert!(!Controls::allows_pointer_click(true, coords));
            assert!(Controls::allows_pointer_click(false, coords));
        }
        assert!(Controls::allows_pointer_click(true, (30.0, 30.0)));
        for coords in [(-1.0, 30.0), (30.0, -1.0), (480.0, 100.0), (200.0, 320.0)] {
            assert!(!Controls::allows_pointer_click(true, coords));
            assert!(!Controls::allows_pointer_click(false, coords));
        }
        // Rejected clicks have no path into set(): held keyboard movement and
        // aim must retain their state and their own balanced synthetic fingers.
        let mut controls = Controls::default();
        controls.set(Input::W, true);
        controls.set(Input::Aim, true);
        assert!(!Controls::allows_pointer_click(true, (440.0, 200.0)));
        assert!(controls.is_held(Input::W));
        assert!(controls.is_held(Input::Aim));
        assert!(controls
            .set(Input::W, false)
            .iter()
            .any(|t| t.action == Action::Movement && t.phase == Phase::Up));
    }

    #[test]
    fn shake_alternates_and_release_or_focus_loss_clears_it() {
        assert_eq!(shake_acceleration_at(Duration::ZERO), (2.0, -2.0, -1.0));
        assert_eq!(
            shake_acceleration_at(Duration::from_millis(40)),
            (-2.0, 2.0, -1.0)
        );
        assert_eq!(
            shake_acceleration_at(Duration::from_millis(80)),
            (2.0, -2.0, -1.0)
        );
        let mut controls = Controls::default();
        controls.set(Input::Shake, true);
        assert!(controls.shake_acceleration().is_some());
        controls.set(Input::Shake, false);
        assert!(controls.shake_acceleration().is_none());
        controls.set(Input::Shake, true);
        controls.clear_on_focus_loss();
        assert!(controls.shake_acceleration().is_none());
    }

    #[test]
    fn mouse_look_consumes_bounded_motion_and_stops_without_drifting() {
        let mut controls = Controls::default();
        controls.mouse_motion(60, -30);
        assert_eq!(controls.mouse_pending, (0.0, 0.0));
        controls.set(Input::Aim, true);
        let now = Instant::now() + Duration::from_millis(100);
        controls.poll_at(now);
        controls.mouse_motion(60, -30);
        let moved = controls.poll_at(now + Duration::from_millis(10));
        assert!(moved.iter().any(|touch| touch.action == Action::Movement
            && touch.phase == Phase::Move
            && touch.coords == (120.0, 200.0)));
        assert_eq!(controls.mouse_pending, (54.0, -24.0));
        for i in 2..=11 {
            controls.poll_at(now + Duration::from_millis(i * 10));
        }
        assert_eq!(controls.mouse_pending, (0.0, 0.0));
        assert_eq!(controls.touches[Action::Movement as usize], None);
        controls.mouse_motion(100, 100);
        controls.clear_on_focus_loss();
        assert_eq!(controls.mouse_pending, (0.0, 0.0));
        assert!(!controls.captures_mouse());
    }

    #[test]
    fn aliases_repeats_and_opposites_keep_one_balanced_movement_touch() {
        let mut controls = Controls::default();
        assert_eq!(controls.set(Input::W, true)[0].phase, Phase::Down);
        assert!(controls.set(Input::W, true).is_empty());
        assert!(controls.set(Input::Up, true).is_empty());
        assert!(controls.set(Input::W, false).is_empty());
        let cancelled = controls.set(Input::Down, true);
        assert_eq!(cancelled[0].phase, Phase::Up);
        assert_eq!(cancelled[0].coords, (72.5, 200.0));
        assert_eq!(controls.set(Input::Up, false)[0].phase, Phase::Down);
        assert_eq!(controls.set(Input::Down, false)[0].phase, Phase::Up);
        assert!(controls.set(Input::Down, false).is_empty());
    }

    #[test]
    fn diagonal_changes_move_existing_touch() {
        let mut controls = Controls::default();
        controls.set(Input::A, true);
        let diagonal = controls.set(Input::S, true);
        assert_eq!(diagonal[0].phase, Phase::Move);
        assert_eq!(diagonal[0].coords, (25.0, 300.0));
        let vertical = controls.set(Input::Left, true);
        assert!(vertical.is_empty());
        assert!(controls.set(Input::A, false).is_empty());
        assert_eq!(controls.set(Input::Left, false)[0].coords, (72.5, 300.0));
    }

    #[test]
    fn fire_and_interaction_share_primary_until_both_released() {
        let mut controls = Controls::default();
        assert_eq!(controls.set(Input::Fire, true)[0].action, Action::Primary);
        assert!(controls.set(Input::Interact, true).is_empty());
        assert!(controls.set(Input::Fire, false).is_empty());
        assert_eq!(controls.set(Input::Interact, false)[0].phase, Phase::Up);
    }

    #[test]
    fn focus_loss_releases_every_action_and_allows_clean_restart() {
        let mut controls = Controls::default();
        for input in [Input::W, Input::Aim, Input::Fire, Input::Reload] {
            controls.set(input, true);
        }
        let releases = controls.clear_on_focus_loss();
        assert!(!releases.is_empty());
        assert_eq!(releases.last().unwrap().phase, Phase::Up);
        assert!(controls.aim_touch.is_none());
        assert!(releases.iter().all(|event| event.phase == Phase::Up));
        let recovery = Instant::now() + Duration::from_secs(1);
        assert_eq!(controls.poll_at(recovery)[0].coords, (440.0, 100.0));
        assert_eq!(
            controls.poll_at(recovery + Duration::from_millis(50))[0].phase,
            Phase::Up
        );
        assert!(controls.clear().is_empty());
        assert_eq!(controls.set(Input::W, true)[0].phase, Phase::Down);
        assert!(!controls.is_held(Input::Aim));
        assert!(controls.reload_acceleration().is_none());
    }

    #[test]
    fn reload_is_a_timed_forward_back_tip_and_repeat_does_not_restart_it() {
        let first = reload_acceleration_at(Duration::ZERO).unwrap();
        let second = reload_acceleration_at(Duration::from_millis(120)).unwrap();
        assert!(first.0 > 3100.0 / 4096.0);
        assert_eq!(first.0, -second.0);
        assert_eq!(first.2, second.2);
        assert!(reload_acceleration_at(Duration::from_millis(240)).is_none());
        let mut controls = Controls::default();
        assert!(controls.set(Input::Reload, true).is_empty());
        let started = controls.reload_started;
        assert!(controls.set(Input::Reload, true).is_empty());
        assert_eq!(controls.reload_started, started);
        controls.clear();
        assert!(controls.reload_acceleration().is_none());
    }

    #[test]
    fn movement_starts_at_center_and_drags_to_target() {
        let mut controls = Controls::default();
        let events = controls.set(Input::W, true);
        assert_eq!(events.len(), 2);
        assert_eq!(events[0].phase, Phase::Down);
        assert_eq!(events[0].coords, (72.5, 250.0));
        assert_eq!(events[1].phase, Phase::Move);
        assert_eq!(events[1].coords, (72.5, 200.0));
        assert_eq!(controls.clear()[0].phase, Phase::Up);
    }

    #[test]
    fn inventory_opens_items_and_escape_closes_even_after_pointer_navigation() {
        let mut controls = Controls::default();
        let now = Instant::now();
        controls.navigate(Input::Inventory, now);
        let first = controls.poll_at(now);
        assert_eq!(first[0].coords, (30.0, 30.0));
        controls.poll_at(now + Duration::from_millis(50));
        assert_eq!(controls.menu_page, Some(0));
        controls.poll_at(now + Duration::from_millis(120));
        controls.poll_at(now + Duration::from_millis(170));
        assert_eq!(controls.menu_page, Some(1));
        controls.observe_pointer_click((455.0, 23.0));
        assert_eq!(controls.menu_page, Some(2));
        controls.navigate(Input::Pause, now + Duration::from_secs(1));
        assert_eq!(
            controls.poll_at(now + Duration::from_secs(1))[0].coords,
            (25.0, 300.0)
        );
        controls.poll_at(now + Duration::from_millis(1050));
        assert_eq!(controls.menu_page, None);
    }

    #[test]
    fn slow_poll_and_focus_loss_keep_menu_touches_balanced() {
        let mut controls = Controls::default();
        let now = Instant::now();
        controls.navigate(Input::Inventory, now);
        assert_eq!(controls.poll_at(now + Duration::from_secs(2)).len(), 1);
        assert!(controls.poll_at(now + Duration::from_secs(2)).is_empty());
        let release = controls.clear();
        assert_eq!(release.len(), 1);
        assert_eq!(release[0].phase, Phase::Up);
        assert!(controls.poll_at(now + Duration::from_secs(9)).is_empty());
        assert!(controls.navigation_touch.is_none());
    }

    #[test]
    fn aim_is_a_tap_fire_uses_the_target_and_release_selects_move_mode() {
        let mut controls = Controls::default();
        let first = controls.set(Input::Aim, true);
        assert_eq!(first[0].coords, (440.0, 200.0));
        assert_eq!(first[0].phase, Phase::Down);
        let now = Instant::now() + Duration::from_secs(1);
        assert_eq!(controls.poll_at(now)[0].phase, Phase::Up);
        assert!(controls.aim_touch.is_none());
        let fire = controls.set(Input::Fire, true);
        assert_eq!(fire[0].coords, (440.0, 200.0));
        controls.set(Input::Fire, false);
        let exit = controls.set(Input::Aim, false);
        assert_eq!(exit[0].coords, (440.0, 100.0));
        assert_eq!(exit[0].phase, Phase::Down);
        assert_eq!(
            controls.poll_at(now + Duration::from_secs(1))[0].phase,
            Phase::Up
        );
        assert!(!controls.aim_mode);
    }
}
