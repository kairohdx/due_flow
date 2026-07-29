import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Pagination } from "./Pagination";

it("navega respeitando os limites da paginação", async () => {
  const user = userEvent.setup();
  const onPageChange = vi.fn();
  render(
    <Pagination
      page={2}
      pages={3}
      total={51}
      onPageChange={onPageChange}
    />,
  );

  await user.click(screen.getByRole("button", { name: "Página anterior" }));
  await user.click(screen.getByRole("button", { name: "Próxima página" }));

  expect(onPageChange).toHaveBeenNthCalledWith(1, 1);
  expect(onPageChange).toHaveBeenNthCalledWith(2, 3);
  expect(screen.getByText("51 itens")).toBeInTheDocument();
});
