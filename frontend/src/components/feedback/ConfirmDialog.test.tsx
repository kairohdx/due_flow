import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ConfirmDialog } from "./ConfirmDialog";

it("leva o foco ao diálogo, fecha com Escape e devolve o foco", async () => {
  const user = userEvent.setup();
  const onCancel = vi.fn();
  const trigger = document.createElement("button");
  trigger.textContent = "Abrir";
  document.body.appendChild(trigger);
  trigger.focus();

  const view = render(
    <ConfirmDialog
      confirmLabel="Confirmar"
      description="Confirme a ação."
      onCancel={onCancel}
      onConfirm={vi.fn()}
      open
      title="Atenção"
    />,
  );

  expect(screen.getByRole("button", { name: "Voltar" })).toHaveFocus();
  await user.keyboard("{Escape}");
  expect(onCancel).toHaveBeenCalledOnce();

  view.unmount();
  expect(trigger).toHaveFocus();
  trigger.remove();
});
