# calculate Laakso Taagepera
def compute_laakso_taagepera_index(proportion_array):
  return 1/sum(map(lambda x: x**2, proportion_array))

print(compute_laakso_taagepera_index([0.75, 0.25]))

array_two = [0.75, 0.10]
for _ in range(15):
  array_two.append(0)

print(compute_laakso_taagepera_index(array_two))
