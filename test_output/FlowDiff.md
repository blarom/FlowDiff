# FlowDiff Analysis Report - FlowDiff

**Generated:** 2026-02-10 01:16:25

## Summary

- **Total Functions:** 38
- **Entry Points:** 38

## Top-Level Entry Points

1. **test_extract_imports_absolute(self)**
   - File: `test_parser.py:29`
   - Qualified: `tests.test_parser.TestExtractImports.test_extract_imports_absolute`

2. **test_extract_imports_from(self)**
   - File: `test_parser.py:57`
   - Qualified: `tests.test_parser.TestExtractImports.test_extract_imports_from`

3. **test_extract_imports_relative_single_dot(self)**
   - File: `test_parser.py:83`
   - Qualified: `tests.test_parser.TestExtractImports.test_extract_imports_relative_single_dot`

4. **test_extract_imports_relative_double_dot(self)**
   - File: `test_parser.py:108`
   - Qualified: `tests.test_parser.TestExtractImports.test_extract_imports_relative_double_dot`

5. **test_extract_imports_malformed_file(self)**
   - File: `test_parser.py:132`
   - Qualified: `tests.test_parser.TestExtractImports.test_extract_imports_malformed_file`

6. **test_extract_functions(self)**
   - File: `test_parser.py:149`
   - Qualified: `tests.test_parser.TestExtractFunctionsAndClasses.test_extract_functions`

7. **test_extract_classes(self)**
   - File: `test_parser.py:168`
   - Qualified: `tests.test_parser.TestExtractFunctionsAndClasses.test_extract_classes`

8. **test_count_lines_of_code(self)**
   - File: `test_parser.py:191`
   - Qualified: `tests.test_parser.TestLinesOfCode.test_count_lines_of_code`

9. **test_resolve_absolute_import(self)**
   - File: `test_parser.py:215`
   - Qualified: `tests.test_parser.TestImportResolution.test_resolve_absolute_import`

10. **test_resolve_relative_import_same_dir(self)**
   - File: `test_parser.py:231`
   - Qualified: `tests.test_parser.TestImportResolution.test_resolve_relative_import_same_dir`

11. **test_resolve_relative_import_parent_dir(self)**
   - File: `test_parser.py:248`
   - Qualified: `tests.test_parser.TestImportResolution.test_resolve_relative_import_parent_dir`

12. **test_resolve_relative_import_grandparent_dir(self)**
   - File: `test_parser.py:265`
   - Qualified: `tests.test_parser.TestImportResolution.test_resolve_relative_import_grandparent_dir`

13. **test_path_to_module_name_simple(self)**
   - File: `test_parser.py:286`
   - Qualified: `tests.test_parser.TestPathToModuleName.test_path_to_module_name_simple`

14. **test_path_to_module_name_root_file(self)**
   - File: `test_parser.py:295`
   - Qualified: `tests.test_parser.TestPathToModuleName.test_path_to_module_name_root_file`

15. **test_path_to_module_name_init_file(self)**
   - File: `test_parser.py:304`
   - Qualified: `tests.test_parser.TestPathToModuleName.test_path_to_module_name_init_file`

16. **test_parse_file_complete(self)**
   - File: `test_parser.py:318`
   - Qualified: `tests.test_parser.TestParseFile.test_parse_file_complete`

17. **test_parse_file_test_detection(self)**
   - File: `test_parser.py:364`
   - Qualified: `tests.test_parser.TestParseFile.test_parse_file_test_detection`

18. **test_filter_external_removes_external_nodes(self)**
   - File: `test_collapser.py:21`
   - Qualified: `tests.test_collapser.TestFilterExternal.test_filter_external_removes_external_nodes`

19. **test_filter_external_preserves_module_edges(self)**
   - File: `test_collapser.py:51`
   - Qualified: `tests.test_collapser.TestFilterExternal.test_filter_external_preserves_module_edges`

20. **test_apply_custom_rules_simple(self)**
   - File: `test_collapser.py:75`
   - Qualified: `tests.test_collapser.TestCustomRules.test_apply_custom_rules_simple`

21. **test_apply_custom_rules_priority(self)**
   - File: `test_collapser.py:113`
   - Qualified: `tests.test_collapser.TestCustomRules.test_apply_custom_rules_priority`

22. **test_group_by_directory_depth_2(self)**
   - File: `test_collapser.py:146`
   - Qualified: `tests.test_collapser.TestGroupByDirectory.test_group_by_directory_depth_2`

23. **test_group_by_directory_depth_1(self)**
   - File: `test_collapser.py:174`
   - Qualified: `tests.test_collapser.TestGroupByDirectory.test_group_by_directory_depth_1`

24. **test_group_by_directory_preserves_edges(self)**
   - File: `test_collapser.py:194`
   - Qualified: `tests.test_collapser.TestGroupByDirectory.test_group_by_directory_preserves_edges`

25. **test_enforce_node_limit_no_merge_if_under(self)**
   - File: `test_collapser.py:224`
   - Qualified: `tests.test_collapser.TestEnforceNodeLimit.test_enforce_node_limit_no_merge_if_under`

26. **test_enforce_node_limit_merges_folders(self)**
   - File: `test_collapser.py:238`
   - Qualified: `tests.test_collapser.TestEnforceNodeLimit.test_enforce_node_limit_merges_folders`

27. **test_collapse_full_pipeline(self)**
   - File: `test_collapser.py:278`
   - Qualified: `tests.test_collapser.TestEndToEndCollapse.test_collapse_full_pipeline`

28. **test_default_config_has_rules(self)**
   - File: `test_collapser.py:314`
   - Qualified: `tests.test_collapser.TestDefaultConfigs.test_default_config_has_rules`

29. **test_stockanalysis_config(self)**
   - File: `test_collapser.py:323`
   - Qualified: `tests.test_collapser.TestDefaultConfigs.test_stockanalysis_config`

30. **test_build_graph_single_file(self)**
   - File: `test_graph.py:22`
   - Qualified: `tests.test_graph.TestGraphBuilder.test_build_graph_single_file`

31. **test_build_graph_with_imports(self)**
   - File: `test_graph.py:53`
   - Qualified: `tests.test_graph.TestGraphBuilder.test_build_graph_with_imports`

32. **test_multiple_imports_same_module(self)**
   - File: `test_graph.py:100`
   - Qualified: `tests.test_graph.TestGraphBuilder.test_multiple_imports_same_module`

33. **test_external_dependency_handling(self)**
   - File: `test_graph.py:136`
   - Qualified: `tests.test_graph.TestGraphBuilder.test_external_dependency_handling`

34. **test_graph_metadata(self)**
   - File: `test_graph.py:179`
   - Qualified: `tests.test_graph.TestGraphBuilder.test_graph_metadata`

35. **test_discover_python_files(self)**
   - File: `test_graph.py:221`
   - Qualified: `tests.test_graph.TestGraphBuilderDiscovery.test_discover_python_files`

36. **test_discover_python_files_empty_directory(self)**
   - File: `test_graph.py:260`
   - Qualified: `tests.test_graph.TestGraphBuilderDiscovery.test_discover_python_files_empty_directory`

37. **test_build_from_directory(self)**
   - File: `test_graph.py:274`
   - Qualified: `tests.test_graph.TestGraphBuilderEndToEnd.test_build_from_directory`

38. **test_build_from_directory_empty(self)**
   - File: `test_graph.py:316`
   - Qualified: `tests.test_graph.TestGraphBuilderEndToEnd.test_build_from_directory_empty`

## Function Call Trees

### [1] test_extract_imports_absolute(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:29`

```
test_extract_imports_absolute()
```

### [2] test_extract_imports_from(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:57`

```
test_extract_imports_from()
```

### [3] test_extract_imports_relative_single_dot(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:83`

```
test_extract_imports_relative_single_dot()
```

### [4] test_extract_imports_relative_double_dot(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:108`

```
test_extract_imports_relative_double_dot()
```

### [5] test_extract_imports_malformed_file(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:132`

```
test_extract_imports_malformed_file()
```

### [6] test_extract_functions(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:149`

```
test_extract_functions()
```

### [7] test_extract_classes(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:168`

```
test_extract_classes()
```

### [8] test_count_lines_of_code(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:191`

```
test_count_lines_of_code()
```

### [9] test_resolve_absolute_import(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:215`

```
test_resolve_absolute_import()
```

### [10] test_resolve_relative_import_same_dir(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:231`

```
test_resolve_relative_import_same_dir()
```

### [11] test_resolve_relative_import_parent_dir(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:248`

```
test_resolve_relative_import_parent_dir()
```

### [12] test_resolve_relative_import_grandparent_dir(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:265`

```
test_resolve_relative_import_grandparent_dir()
```

### [13] test_path_to_module_name_simple(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:286`

```
test_path_to_module_name_simple()
```

### [14] test_path_to_module_name_root_file(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:295`

```
test_path_to_module_name_root_file()
```

### [15] test_path_to_module_name_init_file(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:304`

```
test_path_to_module_name_init_file()
```

### [16] test_parse_file_complete(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:318`

```
test_parse_file_complete()
```

### [17] test_parse_file_test_detection(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_parser.py:364`

```
test_parse_file_test_detection()
```

### [18] test_filter_external_removes_external_nodes(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:21`

```
test_filter_external_removes_external_nodes()
```

### [19] test_filter_external_preserves_module_edges(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:51`

```
test_filter_external_preserves_module_edges()
```

### [20] test_apply_custom_rules_simple(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:75`

```
test_apply_custom_rules_simple()
```

### [21] test_apply_custom_rules_priority(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:113`

```
test_apply_custom_rules_priority()
```

### [22] test_group_by_directory_depth_2(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:146`

```
test_group_by_directory_depth_2()
```

### [23] test_group_by_directory_depth_1(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:174`

```
test_group_by_directory_depth_1()
```

### [24] test_group_by_directory_preserves_edges(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:194`

```
test_group_by_directory_preserves_edges()
```

### [25] test_enforce_node_limit_no_merge_if_under(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:224`

```
test_enforce_node_limit_no_merge_if_under()
```

### [26] test_enforce_node_limit_merges_folders(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:238`

```
test_enforce_node_limit_merges_folders()
```

### [27] test_collapse_full_pipeline(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:278`

```
test_collapse_full_pipeline()
```

### [28] test_default_config_has_rules(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:314`

```
test_default_config_has_rules()
```

### [29] test_stockanalysis_config(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_collapser.py:323`

```
test_stockanalysis_config()
```

### [30] test_build_graph_single_file(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_graph.py:22`

```
test_build_graph_single_file()
```

### [31] test_build_graph_with_imports(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_graph.py:53`

```
test_build_graph_with_imports()
```

### [32] test_multiple_imports_same_module(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_graph.py:100`

```
test_multiple_imports_same_module()
```

### [33] test_external_dependency_handling(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_graph.py:136`

```
test_external_dependency_handling()
```

### [34] test_graph_metadata(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_graph.py:179`

```
test_graph_metadata()
```

### [35] test_discover_python_files(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_graph.py:221`

```
test_discover_python_files()
```

### [36] test_discover_python_files_empty_directory(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_graph.py:260`

```
test_discover_python_files_empty_directory()
```

### [37] test_build_from_directory(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_graph.py:274`

```
test_build_from_directory()
```

### [38] test_build_from_directory_empty(self)

**Location:** `/Users/barlarom/PycharmProjects/Main/FlowDiff/tests/test_graph.py:316`

```
test_build_from_directory_empty()
```
