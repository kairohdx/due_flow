import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  configureAutomation,
  disableAutomation,
  enableAutomation,
  getAutomation,
} from "../api/dashboard";
import { changePassword, type ChangePasswordPayload } from "../api/settings";

export function useSettings() {
  const queryClient = useQueryClient();
  const automation = useQuery({
    queryKey: ["automation"],
    queryFn: getAutomation,
    placeholderData: (previous) => previous,
  });
  const updateState = (state: Awaited<ReturnType<typeof getAutomation>>) => {
    queryClient.setQueryData(["automation"], state);
  };
  const configure = useMutation({
    mutationFn: (intervalSeconds: number) =>
      configureAutomation(intervalSeconds),
    onSuccess: updateState,
  });
  const enable = useMutation({
    mutationFn: () => enableAutomation(),
    onSuccess: updateState,
  });
  const disable = useMutation({
    mutationFn: () => disableAutomation(),
    onSuccess: updateState,
  });
  const password = useMutation({
    mutationFn: (payload: ChangePasswordPayload) => changePassword(payload),
  });
  return { automation, configure, enable, disable, password };
}
