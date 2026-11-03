# Design System – PeerShare

## 1. Design Direction

PeerShare follows a modern, minimal and warm visual design.

The interface should feel:

* Clean and uncluttered.
* Friendly and approachable.
* Modern, with soft rounded elements.
* Easy to understand and navigate.
* Consistent across sender and receiver interfaces.

Use the generated dashboard mockup as the primary visual reference.

## 2. Colour Palette

Use the following colour tokens consistently throughout the application.

```css
:root {
  --bg-dark: oklch(0.92 0.07 44);
  --bg: oklch(0.96 0.07 44);
  --bg-light: oklch(1 0.07 44);

  --text: oklch(0.15 0.14 44);
  --text-muted: oklch(0.4 0.14 44);

  --highlight: oklch(1 0.14 44);

  --border: oklch(0.6 0.14 44);
  --border-muted: oklch(0.7 0.14 44);

  --primary: oklch(0.4 0.14 44);
  --secondary: oklch(0.4 0.14 224);

  --danger: oklch(0.5 0.14 30);
  --warning: oklch(0.5 0.14 100);
  --success: oklch(0.5 0.14 160);
  --info: oklch(0.5 0.14 260);
}
```

### Colour Usage

| Token            | Purpose                                |
| ---------------- | -------------------------------------- |
| Background       | Main application background            |
| Background Dark  | Sidebar and secondary surfaces         |
| Background Light | Cards, panels and elevated surfaces    |
| Text             | Primary headings and content           |
| Text Muted       | Supporting text and descriptions       |
| Primary          | Main buttons and important actions     |
| Secondary        | Secondary actions and highlights       |
| Success          | Successful transfers and online status |
| Danger           | Failed transfers and errors            |
| Warning          | Pending operations and warnings        |
| Info             | Informational messages                 |

Do not introduce unrelated colours without a clear functional requirement.

## 3. Typography

Use a clean sans-serif typeface throughout the application.

Typography hierarchy:

* Page Heading: 28–32px, semibold/bold.
* Section Heading: 18–22px, semibold.
* Card Heading: 16–18px, semibold.
* Body Text: 14–16px, regular.
* Supporting Text: 12–14px, regular.
* Labels: 12–14px, medium.

Maintain consistent font weights and line heights.

## 4. Border Radius and Shapes

Rounded elements are a defining part of the PeerShare visual identity.

| Component         | Border Radius        |
| ----------------- | -------------------- |
| Primary Buttons   | Fully rounded / pill |
| Secondary Buttons | Fully rounded / pill |
| Input Fields      | 12–16px              |
| Cards             | 16–20px              |
| Modals            | 20px                 |
| Badges            | Fully rounded        |
| Navigation Items  | 10–12px              |
| Device Cards      | 16–20px              |

Avoid sharp corners and overly rectangular UI elements.

## 5. Buttons

### Primary Button

* Uses the primary colour.
* Fully rounded shape.
* Clear action-oriented label.
* Subtle hover transition.
* Visible disabled state.

### Secondary Button

* Uses a light background or outlined appearance.
* Fully rounded shape.
* Used for less important actions.

### Danger Button

* Uses the danger colour.
* Reserved for destructive or critical actions.

Buttons should have consistent height, padding and typography.

## 6. Cards and Containers

Cards should:

* Use the light background colour.
* Have rounded corners.
* Use subtle borders or shadows.
* Maintain consistent internal padding.
* Clearly separate content sections.

Avoid excessive shadows, borders or unnecessary visual decoration.

## 7. Input Fields

Input fields should:

* Have rounded corners.
* Use consistent padding.
* Have clearly visible labels.
* Include focus and error states.
* Maintain sufficient contrast.

Apply the same styling to text fields, search fields and numeric inputs.

## 8. Status Indicators

Use semantic colours consistently.

* Green: Connected, completed, successful.
* Red: Failed, disconnected, error.
* Yellow: Pending, waiting, warning.
* Blue: Information and active operations.

Status badges should use fully rounded shapes.

## 9. Layout and Spacing

Follow a consistent spacing scale:

* 4px – Very small gaps.
* 8px – Small gaps.
* 12px – Compact spacing.
* 16px – Standard spacing.
* 24px – Section spacing.
* 32px – Large spacing.
* 48px – Major layout separation.

Maintain sufficient whitespace between sections.

## 10. Application Layout

Follow the overall layout and visual hierarchy of the approved mockup.

The application should include:

* Sidebar navigation.
* Main content area.
* Dashboard overview.
* Device discovery and connection section.
* File transfer interface.
* Transfer progress and visualization.
* Transfer history.
* Settings.

The sender and receiver interfaces should maintain the same visual language while displaying role-specific functionality.

## 11. Animations and Interactions

Use subtle animations for:

* Button hover and click states.
* Card interactions.
* Page transitions.
* Device connection states.
* File transfer progress.
* Frame transmission and ACK visualization.

Animations should communicate actual application events.

Do not use decorative animations that could be confused with real network activity.

## 12. Responsive Design

The interface should adapt to:

* Desktop screens.
* Laptop screens.
* Tablet screens.

Prioritise the desktop experience because the application is intended for laptop-to-laptop file transfers.

## 13. Implementation Guidelines

* Use the defined colour variables instead of hardcoding colours.
* Maintain reusable components.
* Keep spacing, typography and border radius consistent.
* Avoid unnecessary gradients and decorative effects.
* Use Lucide React for icons.
* Use Motion for meaningful UI animations.
* Maintain consistent styling across all application pages.
* Follow this document as the single source of truth for UI styling.

## 14. Visual Reference

The approved PeerShare dashboard mockup is the primary visual reference.

The implementation should preserve its:

* Warm colour palette.
* Clean dashboard layout.
* Rounded buttons and components.
* Soft card appearance.
* Minimal visual hierarchy.
* Friendly and modern aesthetic.

Do not redesign the interface independently of this direction.
